from collections.abc import AsyncGenerator, Callable
from contextlib import _AsyncGeneratorContextManager, asynccontextmanager
from contextlib import AsyncExitStack
from typing import Any
from sqlalchemy.ext.asyncio.session import AsyncSession
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER
from fastapi.responses import StreamingResponse
from io import BytesIO
import xml.etree.ElementTree as ET
from xml.dom import minidom
from uuid import UUID
from uuid import uuid4
import asyncio
import json
import pydicom
import anyio
import fastapi
import redis.asyncio as redis
from arq import create_pool
from sqlalchemy.orm import selectinload
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, FastAPI,Request, Response, Form
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.templating import Jinja2Templates
from fastapi import UploadFile, File, Form
from pathlib import Path
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, PlainTextResponse
from ..importers.xml_importer import import_xml_template 

from .logger import logging
import openslide
from openslide.deepzoom import DeepZoomGenerator

from ..api.dependencies import get_current_superuser
from ..middleware.client_cache_middleware import ClientCacheMiddleware
from .config import (
    AppSettings,
    ClientSideCacheSettings,
    DatabaseSettings,
    EnvironmentOption,
    EnvironmentSettings,
    RedisCacheSettings,
    RedisQueueSettings,
    RedisRateLimiterSettings,
    settings,
)
import sqlalchemy as sa
import uuid
from datetime import datetime
from sqlalchemy import select
from .db.database import Base, async_engine as engine
from .db.database import async_get_db
from .utils import cache, queue, rate_limit
from ..models import *
from ..models.enums import ReportType
from ..validators.validate_xml import validate_xml_structure

#Logger
logger = logging.getLogger(__name__)

# -------------- create --------------
# Define templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# Define a test slide load in
#SLIDES_DIR = Path(__file__).parent / "slides" 
# Needs fixing for configurable value
SLIDES_DIR = Path("/code/slides") 
logger.info(f"Checking slides directory: {SLIDES_DIR}") 

# Initialize Jinja2
templates = Jinja2Templates(directory=TEMPLATES_DIR)

#Function to scan slides on start:
async def register_slides_from_folder(slide_dir: Path, db: AsyncSession):
    """Scan /slides and create Slide records for any that aren't already in the DB."""
    slide_formats = {".svs", ".tiff", ".ndpi", ".vms", ".vmu", ".scn", ".mrxs", ".bif"}

    for item in slide_dir.iterdir():
        # Determine slide name for DB
        if item.is_file() and item.suffix.lower() in slide_formats:
            slide_name = item.name
        elif item.is_dir() and any(f.suffix.lower() in {".dcm", ".mrxs", ".dat"} for f in item.iterdir()):
            slide_name = item.name
        else:
            continue  # Not a supported slide

        # Check if it already exists in DB
        existing = await db.execute(select(Slide).where(Slide.slide_name == slide_name))
        if not existing.scalar_one_or_none():
            new_slide = Slide(
                id=uuid4(),
                slide_name=slide_name,
                slide_label=None,
                slide_barcode=None,
                case_identifier=None,
            )
            db.add(new_slide)
            logger.info(f"Registered new slide in DB: {slide_name}")

    await db.commit()

# -------------- deepzoom --------------
# Function to create DeepZoom tiles
def get_deepzoom(slide_path):
    """Generate DeepZoom tiles from an OpenSlide image."""
    slide = openslide.OpenSlide(str(slide_path))
    return DeepZoomGenerator(slide, tile_size=256, overlap=1, limit_bounds=True)



def extract_filtered_metadata(dicom_sample):
    """Extract DICOM metadata while **excluding** base64/binary fields."""
    dicom_dict = {}

    for tag in dicom_sample.keys():
        tag_data = dicom_sample[tag].value

        # **Skip pixel data & known large binary fields**
        if tag in [pydicom.tag.Tag(0x7FE00010), pydicom.tag.Tag(0x00420011)]:  
            continue  # Skip pixel data (huge binary) & encapsulated PDFs

        # **Skip large binary fields automatically** (anything over 1000 chars)
        if isinstance(tag_data, bytes) and len(tag_data) > 1000:
            continue  # Prevents dumping large base64 data
        
        # **Convert to string for safe JSON serialization**
        dicom_dict[str(tag)] = str(tag_data)

    return dicom_dict

# -------------- database --------------
async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# -------------- cache --------------
async def create_redis_cache_pool() -> None:
    cache.pool = redis.ConnectionPool.from_url(settings.REDIS_CACHE_URL)
    cache.client = redis.Redis.from_pool(cache.pool)  # type: ignore


async def close_redis_cache_pool() -> None:
    await cache.client.aclose()  # type: ignore


# -------------- queue --------------
async def create_redis_queue_pool() -> None:
    queue.pool = await create_pool(RedisSettings(host=settings.REDIS_QUEUE_HOST, port=settings.REDIS_QUEUE_PORT))


async def close_redis_queue_pool() -> None:
    await queue.pool.aclose()  # type: ignore


# -------------- rate limit --------------
async def create_redis_rate_limit_pool() -> None:
    rate_limit.pool = redis.ConnectionPool.from_url(settings.REDIS_RATE_LIMIT_URL)
    rate_limit.client = redis.Redis.from_pool(rate_limit.pool)  # type: ignore


async def close_redis_rate_limit_pool() -> None:
    await rate_limit.client.aclose()  # type: ignore


# -------------- application --------------
async def set_threadpool_tokens(number_of_tokens: int = 100) -> None:
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = number_of_tokens


def lifespan_factory(
    settings: (
        DatabaseSettings
        | RedisCacheSettings
        | AppSettings
        | ClientSideCacheSettings
        | RedisQueueSettings
        | RedisRateLimiterSettings
        | EnvironmentSettings
    ),
    create_tables_on_start: bool = True,
) -> Callable[[FastAPI], _AsyncGeneratorContextManager[Any]]:
    """Factory to create a lifespan async context manager for a FastAPI app."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator:
        await set_threadpool_tokens()
        db: AsyncSession | None = None
        stack = AsyncExitStack()

        try:
            # Setup section
            if isinstance(settings, DatabaseSettings) and create_tables_on_start:
                await create_tables()

            if isinstance(settings, RedisCacheSettings):
                await create_redis_cache_pool()

            if isinstance(settings, RedisQueueSettings):
                await create_redis_queue_pool()

            if isinstance(settings, RedisRateLimiterSettings):
                await create_redis_rate_limit_pool()

            #Open DB session manually
            db_gen = async_get_db()
            db = await anext(db_gen)

            # Scan slides folder and insert missing Slide entries
            existing_slide_names = set()
            result = await db.execute(select(Slide.slide_name))
            existing_slide_names.update(row[0] for row in result.all())

            new_slides = []

            for slide_file in SLIDES_DIR.iterdir():
                if not slide_file.is_file():
                    continue

                if slide_file.name not in existing_slide_names:
                    new_slides.append(
                        Slide(
                            slide_name=slide_file.name
                        )
                    )

            if new_slides:
                db.add_all(new_slides)
                await db.commit()
                logging.info(f"Inserted {len(new_slides)} new slides on startup.")

            yield

        except Exception as e:
            logging.exception("Error during application lifespan setup: %s", str(e))
            raise

        finally:
            if db:
                await db.close()

            if isinstance(settings, RedisCacheSettings):
                await close_redis_cache_pool()

            if isinstance(settings, RedisQueueSettings):
                await close_redis_queue_pool()

            if isinstance(settings, RedisRateLimiterSettings):
                await close_redis_rate_limit_pool()

    return lifespan

#------------Functions------------
async def get_current_profile(
    request: Request,
    db: AsyncSession = Depends(async_get_db),
) -> Profile | None:
    profile_id = request.session.get("profile_id")
    if not profile_id:
        return None
    result = await db.execute(sa.select(Profile).where(Profile.id == profile_id))
    return result.scalar_one_or_none()
# -------------- application --------------
def create_application(
    router: APIRouter,
    settings: (
        DatabaseSettings
        | RedisCacheSettings
        | AppSettings
        | ClientSideCacheSettings
        | RedisQueueSettings
        | RedisRateLimiterSettings
        | EnvironmentSettings
    ),
    create_tables_on_start: bool = True,
    **kwargs: Any,
) -> FastAPI:
    """Creates and configures a FastAPI application based on the provided settings.

    This function initializes a FastAPI application and configures it with various settings
    and handlers based on the type of the `settings` object provided.

    Parameters
    ----------
    router : APIRouter
        The APIRouter object containing the routes to be included in the FastAPI application.

    settings
        An instance representing the settings for configuring the FastAPI application.
        It determines the configuration applied:

        - AppSettings: Configures basic app metadata like name, description, contact, and license info.
        - DatabaseSettings: Adds event handlers for initializing database tables during startup.
        - RedisCacheSettings: Sets up event handlers for creating and closing a Redis cache pool.
        - ClientSideCacheSettings: Integrates middleware for client-side caching.
        - RedisQueueSettings: Sets up event handlers for creating and closing a Redis queue pool.
        - RedisRateLimiterSettings: Sets up event handlers for creating and closing a Redis rate limiter pool.
        - EnvironmentSettings: Conditionally sets documentation URLs and integrates custom routes for API documentation
          based on the environment type.

    create_tables_on_start : bool
        A flag to indicate whether to create database tables on application startup.
        Defaults to True.

    **kwargs
        Additional keyword arguments passed directly to the FastAPI constructor.

    Returns
    -------
    FastAPI
        A fully configured FastAPI application instance.

    The function configures the FastAPI application with different features and behaviors
    based on the provided settings. It includes setting up database connections, Redis pools
    for caching, queue, and rate limiting, client-side caching, and customizing the API documentation
    based on the environment settings.
    """
    # --- before creating application ---
    if isinstance(settings, AppSettings):
        to_update = {
            "title": settings.APP_NAME,
            "description": settings.APP_DESCRIPTION,
            "contact": {"name": settings.CONTACT_NAME, "email": settings.CONTACT_EMAIL},
            "license_info": {"name": settings.LICENSE_NAME},
        }
        kwargs.update(to_update)

    if isinstance(settings, EnvironmentSettings):
        kwargs.update({"docs_url": None, "redoc_url": None, "openapi_url": None})

    lifespan = lifespan_factory(settings, create_tables_on_start=create_tables_on_start)

    application = FastAPI(lifespan=lifespan, **kwargs)
    application.include_router(router)

    #Session middleware:
    application.add_middleware(SessionMiddleware, secret_key="dev-secret-key-change-this")


    # Add Jinja2 templates to FastAPI
    application.state.templates = templates

    # Log when the app starts
    logger.info("PathWay Application has started.")

    async def render_template(request: Request, template_name: str, context: dict[str, Any] = None):
        """Render a Jinja2 template and log errors."""
        try:
            logger.info(f"Rendering template: {template_name}")
            context = context or {}
            context["request"] = request
            return templates.TemplateResponse(template_name, context)
        except Exception as e:
            logger.error(f"Error rendering {template_name}: {e}", exc_info=True)
            return HTMLResponse(content=f"<h1>500 Internal Server Error</h1><p>{e}</p>", status_code=500)


    #Main Section

    @application.get("/", response_class=HTMLResponse)
    async def home_page(request: Request):
        return await render_template(request, "index.html")

    @application.get("/settings", response_class=HTMLResponse)
    async def settings_page(request: Request, db: AsyncSession = Depends(async_get_db)):
        result = await db.execute(sa.select(Profile))  # `sa` is shorthand for `sqlalchemy`
        profiles = result.scalars().all()

        current_profile_id = request.session.get("profile_id")

        return await render_template(request, "settings.html", {
            "profiles": profiles,
            "current_profile_id": current_profile_id,
        })

    #POST For Profiles
    @application.post("/settings")
    async def set_profile(request: Request, profile_id: str = Form(...)):
        request.session["profile_id"] = profile_id
        return RedirectResponse(url="/settings", status_code=HTTP_303_SEE_OTHER)

    #Create new profile:
    @application.post("/settings/create", response_class=HTMLResponse)
    async def create_new_profile(
        request: Request,
        name: str = Form(...),
        db: AsyncSession = Depends(async_get_db),
    ):
        
        # Check for duplicates
        result = await db.execute(sa.select(Profile).where(Profile.name == name))
        if result.scalar_one_or_none():
            return await render_template(request, "settings.html", {
                "success_message": f"A profile named '{name}' already exists.",
                "profiles": (await db.execute(sa.select(Profile))).scalars().all(),
                "current_profile_id": request.session.get("profile_id"),
            })

        profile = Profile(name=name)
        db.add(profile)
        await db.commit()

        logger.info(f"Created new profile: {name} (id={profile.id})")

        return await render_template(request, "settings.html", {
            "success_message": f"Created new profile: {name}",
            "profiles": (await db.execute(sa.select(Profile))).scalars().all(),
            "current_profile_id": request.session.get("profile_id"),
        })

    @application.get("/report", response_class=HTMLResponse)
    async def report_page(request: Request):
        return await render_template(request, "report.html")

    @application.get("/database", response_class=HTMLResponse)
    async def database_page(request: Request):
        return await render_template(request, "database.html")
    #Mapping expanded to include editing mappings
    @application.get("/mapping", response_class=HTMLResponse)
    async def mapping_page(request: Request, db: AsyncSession = Depends(async_get_db)):
        try:
            profile_id = request.session.get("profile_id")
            if not profile_id:
                return HTMLResponse("<h3>Error: No profile selected.</h3>", status_code=400)

            stmt = (
                select(TemplateVersion)
                .where(TemplateVersion.profile_id == UUID(profile_id))
                .where(TemplateVersion.version_is_active == True)
                .options(selectinload(TemplateVersion.groups).selectinload(TemplateGroup.properties))
            )

            result = await db.execute(stmt)
            active_version = result.scalars().first()

            if not active_version:
                return HTMLResponse("<h3>No active template version found for this profile.</h3>", status_code=404)

            return templates.TemplateResponse("mapping.html", {
                "request": request,
                "active_version": active_version
            })

        except Exception as e:
            logger.exception("Error rendering mapping page")
            return HTMLResponse(content=f"<h3>Internal Server Error: {str(e)}</h3>", status_code=500)

    @application.post("/update_mappings")
    async def update_mappings(
        request: Request,
        db: AsyncSession = Depends(async_get_db),
    ):
        """
        Updates path mappings for a batch of template properties.
        Ensures per-field validation, logs each change, and rolls back on partial failure.
        """
        try:
            updates = await request.json()
            if not isinstance(updates, list):
                return JSONResponse({"error": "Invalid payload format. Expected a list."}, status_code=400)

            errors = []
            for i, mapping in enumerate(updates):
                prop_id = mapping.get("id")
                if not prop_id:
                    errors.append(f"Missing 'id' in item {i}")
                    continue

                try:
                    stmt = select(TemplateProperty).where(TemplateProperty.id == int(prop_id))
                    result = await db.execute(stmt)
                    prop: TemplateProperty = result.scalar_one_or_none()

                    if not prop:
                        errors.append(f"Property with id {prop_id} not found.")
                        continue

                    # Validate each mapping path (example: ensure it's a non-empty string)
                    for field in ["fhir_mapping", "hl7v2_path", "dicom_path", "json_path"]:
                        value = mapping.get(field)
                        if value is not None and not isinstance(value, str):
                            errors.append(f"Invalid value for '{field}' in property {prop_id}")
                            continue

                    logger.info(f"Updating property {prop_id} with: {mapping}")

                    # Apply updates
                    prop.fhir_mapping = mapping.get("fhir_mapping")
                    prop.hl7v2_path = mapping.get("hl7v2_path")
                    prop.dicom_path = mapping.get("dicom_path")
                    prop.json_path = mapping.get("json_path")

                except Exception as item_err:
                    logger.exception(f"Error updating property {prop_id}: {item_err}")
                    errors.append(f"Exception updating property {prop_id}: {str(item_err)}")

            # If any errors occurred, rollback all changes and return error list
            if errors:
                logger.warning("Update failed with errors. Rolling back.")
                await db.rollback()
                return JSONResponse({"status": "error", "errors": errors}, status_code=400)

            # Commit only if all went well
            await db.commit()
            logger.info("All mappings updated successfully.")
            return JSONResponse({"status": "success"})

        except Exception as e:
            logger.exception("Unexpected error in mapping update")
            await db.rollback()
            return JSONResponse({"error": f"Unexpected error: {str(e)}"}, status_code=500)

    @application.get("/export_template_xml")
    async def export_template_xml(
        request: Request,
        db: AsyncSession = Depends(async_get_db)
    ):
        profile_id = request.session.get("profile_id")
        if not profile_id:
            return HTMLResponse("<h3>No profile selected.</h3>", status_code=400)

        try:
            stmt = (
                select(TemplateVersion)
                .where(TemplateVersion.profile_id == UUID(profile_id))
                .where(TemplateVersion.version_is_active == True)
                .options(selectinload(TemplateVersion.groups).selectinload(TemplateGroup.properties))
            )
            result = await db.execute(stmt)
            active_version = result.scalars().first()

            if not active_version:
                return HTMLResponse("<h3>No active version found.</h3>", status_code=404)

            # Build XML
            root = ET.Element("Template")
            for group in active_version.groups:
                group_el = ET.SubElement(root, "Group", name=group.name)
                for prop in group.properties:
                    prop_attrs = {
                        "name": prop.name,
                        "type": prop.datatype or "string"
                    }
                    if prop.external_id:
                        prop_attrs["id"] = prop.external_id
                    if prop.json_path:
                        prop_attrs["jsonPath"] = prop.json_path
                    if prop.xml_path:
                        prop_attrs["xmlPath"] = prop.xml_path
                    if prop.fhir_mapping:
                        prop_attrs["fhirMapping"] = prop.fhir_mapping
                    if prop.hl7v2_path:
                        prop_attrs["hl7v2Path"] = prop.hl7v2_path
                    if prop.dicom_path:
                        prop_attrs["dicomPath"] = prop.dicom_path
                    if prop.is_array:
                        prop_attrs["array"] = "true"
                    if prop.is_object:
                        prop_attrs["object"] = "true"
                    if prop.constraints:
                        allowed_values = prop.constraints.get("allowed_values")
                        required = prop.constraints.get("required")
                        constraints = []
                        if allowed_values:
                            constraints.append("allowed_values:" + "|".join(allowed_values))
                        if required is not None:
                            constraints.append("required:" + str(required).lower())
                        if constraints:
                            prop_attrs["constraints"] = ";".join(constraints)

                    ET.SubElement(group_el, "Property", prop_attrs)

            rough_string = ET.tostring(root, encoding="utf-8")
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ", encoding="utf-8")

            buf = BytesIO(pretty_xml)
            filename = f"template_export_{active_version.version}.xml"

            return StreamingResponse(
                content=buf,
                media_type="application/xml",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

        except Exception as e:
            logger.exception("Error exporting template XML")
            return HTMLResponse(f"<h3>Error exporting XML: {str(e)}</h3>", status_code=500)
    
    @application.get("/export_template_json")
    async def export_template_json(request: Request, db: AsyncSession = Depends(async_get_db)):
        try:
            profile_id = request.session.get("profile_id")
            if not profile_id:
                return HTMLResponse(content="<h3>Error: No profile selected.</h3>", status_code=400)

            stmt = (
                select(TemplateVersion)
                .where(TemplateVersion.profile_id == UUID(profile_id))
                .where(TemplateVersion.version_is_active == True)
                .options(selectinload(TemplateVersion.groups).selectinload(TemplateGroup.properties))
            )

            result = await db.execute(stmt)
            version = result.scalars().first()

            if not version:
                return HTMLResponse("<h3>No active template version found for this profile.</h3>", status_code=404)

            # Structure the template data
            data = {
                "version": version.version,
                "profile_id": str(version.profile_id),
                "groups": []
            }

            for group in version.groups:
                group_data = {
                    "name": group.name,
                    "properties": []
                }
                for prop in group.properties:
                    prop_data = {
                        "name": prop.name,
                        "type": prop.datatype,
                        "is_array": prop.is_array,
                        "is_object": prop.is_object,
                        "external_id": prop.external_id,
                        "json_path": prop.json_path,
                        "xml_path": prop.xml_path,
                        "fhir_mapping": prop.fhir_mapping,
                        "hl7v2_path": prop.hl7v2_path,
                        "dicom_path": prop.dicom_path,
                        "constraints": prop.constraints or {}
                    }
                    group_data["properties"].append(prop_data)
                data["groups"].append(group_data)

            json_str = json.dumps(data, indent=2)  # Pretty-printed JSON
            return StreamingResponse(
                content=BytesIO(json_str.encode("utf-8")),
                media_type="application/json",
                headers={
                    "Content-Disposition": "attachment; filename=template_export.json"
                },
            )

        except Exception as e:
            logger.exception("Error exporting template JSON")
            return HTMLResponse(
                content=f"<h3>Internal Server Error: {str(e)}</h3>",
                status_code=500
            )
    #Temp HL7 exporter - will be abstracted and will put verify/parser in:
    @application.get("/export_template_hl7v2")
    async def export_hl7v2(request: Request, db: AsyncSession = Depends(async_get_db)):
        try:
            profile_id = request.session.get("profile_id")
            if not profile_id:
                return PlainTextResponse("No profile selected.", status_code=400)

            stmt = (
                select(TemplateVersion)
                .where(TemplateVersion.profile_id == UUID(profile_id))
                .where(TemplateVersion.version_is_active == True)
                .options(selectinload(TemplateVersion.groups).selectinload(TemplateGroup.properties))
            )
            result = await db.execute(stmt)
            version = result.scalars().first()

            if not version:
                return PlainTextResponse("No active template version found.", status_code=404)

            hl7_segments = {}

            for group in version.groups:
                for prop in group.properties:
                    if not prop.hl7v2_path:
                        continue

                    path_parts = prop.hl7v2_path.strip().split("-")
                    segment = path_parts[0]
                    field = int(path_parts[1]) if len(path_parts) > 1 else 1
                    component = int(path_parts[2]) if len(path_parts) > 2 else 0

                    if segment not in hl7_segments:
                        hl7_segments[segment] = {}

                    if field not in hl7_segments[segment]:
                        hl7_segments[segment][field] = []

                    while len(hl7_segments[segment][field]) < component:
                        hl7_segments[segment][field].append("")

                    if component == 0:
                        hl7_segments[segment][field] = [prop.name]
                    else:
                        while len(hl7_segments[segment][field]) < component:
                            hl7_segments[segment][field].append("")
                        hl7_segments[segment][field][component - 1] = prop.name

            output_lines = []
            for segment, fields in hl7_segments.items():
                max_field = max(fields.keys())
                hl7_fields = [""] * max_field
                for field_num, comps in fields.items():
                    if isinstance(comps, list):
                        hl7_fields[field_num - 1] = "^".join(comps)
                    else:
                        hl7_fields[field_num - 1] = comps
                segment_str = f"{segment}|" + "|".join(hl7_fields)
                output_lines.append(segment_str)

            # Prepare file-like stream
            hl7_bytes = "\n".join(output_lines).encode("utf-8")
            stream = BytesIO(hl7_bytes)

            return StreamingResponse(
                stream,
                media_type="text/plain",
                headers={
                    "Content-Disposition": 'attachment; filename="hl7_export.txt"'
                }
            )

        except Exception as e:
            logger.exception("Error exporting HL7 v2 message")
            return PlainTextResponse(f"Internal Server Error: {str(e)}", status_code=500)
    
    @application.get("/upload", response_class=HTMLResponse)
    async def upload_page(request: Request):
        return await render_template(request, "upload.html")

    @application.get("/upload_ds", response_class=HTMLResponse)
    async def upload_ds_page(request: Request):
        return await render_template(request, "upload_ds.html")
    
    #XML Uploader
    @application.get("/upload_xml", response_class=HTMLResponse)
    async def upload_xml_page(request: Request):
        return await render_template(request, "upload_xml.html")


    @application.post("/upload_xml", response_class=HTMLResponse)
    async def upload_xml(
        request: Request,
        xml_file: UploadFile = File(...),
        db: AsyncSession = Depends(async_get_db)
    ):
        profile_id = request.session.get("profile_id")
        if not profile_id:
            logger.warning("Attempted upload without a selected profile.")
            return HTMLResponse(content="<h3>Error: No profile selected.</h3>", status_code=400)

        try:
            xml_content = await xml_file.read()
            xml_str = xml_content.decode("utf-8")
        except Exception as e:
            logger.error("Failed to read uploaded XML: %s", str(e))
            return HTMLResponse(content=f"<h3>Error reading uploaded XML file: {e}</h3>", status_code=500)

        try:
            version = await asyncio.wait_for(
                import_xml_template(db, xml_str, profile_id=UUID(profile_id)),
                timeout=10  # seconds — adjust as needed
            )

            if version is None:
                return HTMLResponse(content="<h3>Failed to import XML template.</h3>", status_code=500)

            return await render_template(request, "upload_xml.html", {
                "success_message": f"Template imported as version {version.version}."
            })

        except asyncio.TimeoutError:
            logger.error("XML import timed out.")
            await db.rollback()
            return HTMLResponse(
                content="<h3>XML import timed out. Please check the size or structure of your file.</h3>",
                status_code=504
            )
        except Exception as e:
            logger.exception("Unexpected error in XML import")
            await db.rollback()
            return HTMLResponse(content=f"<h3>Unexpected error: {str(e)}</h3>", status_code=500)
    # Validate xml

    @application.get("/validate_xml", response_class=HTMLResponse)
    async def validate_xml_page(request: Request):
        return await render_template(request, "validate_xml.html")

    @application.post("/validate_xml", response_class=HTMLResponse)
    async def validate_xml(
        request: Request,
        xml_file: UploadFile = File(...),
        db: AsyncSession = Depends(async_get_db)
    ):
        profile_id = request.session.get("profile_id")
        if not profile_id:
            return HTMLResponse(content="<h3>No profile selected.</h3>", status_code=400)

        try:
            xml_content = await xml_file.read()
            xml_str = xml_content.decode("utf-8")
        except Exception as e:
            logger.error("Error reading file: %s", str(e))
            return HTMLResponse(content=f"<h3>Error reading uploaded XML file: {e}</h3>", status_code=500)

        errors = await validate_xml_structure(db, xml_str, UUID(profile_id))
        if not errors:
            return await render_template(request, "validate_xml.html", {
                "success_message": "Validation passed! Uploaded XML matches the active version."
            })
        else:
            return await render_template(request, "validate_xml.html", {
                "error_messages": errors
            })

    # Example Sections For Demonstrations And Setup
    @application.get("/fhir_example", response_class=HTMLResponse)
    async def fhir_example_page(request: Request):
        return await render_template(request, "fhir_example.html")
    
    @application.get("/xml_example", response_class=HTMLResponse)
    async def xml_example_page(request: Request):
        return await render_template(request, "xml_example.html")
    
    @application.get("/sdc_example", response_class=HTMLResponse)
    async def sdc_example_page(request: Request):
        return await render_template(request, "sdc_example.html")
    
    # SDC Section Reload
    @application.get("/sdc_overview", response_class=HTMLResponse)
    async def sdc_overview_page(request: Request):
        return await render_template(request, "sdc_overview.html")
    
    @application.get("/sdc_guidelines", response_class=HTMLResponse)
    async def sdc_overview_page(request: Request):
        return await render_template(request, "sdc_guidelines.html")

    # ---------- Viewer Route ----------
    @application.get("/viewer", response_class=HTMLResponse)
    async def viewer_page(request: Request):
        """Render the DeepZoom viewer page with all supported slides (files & folders)."""
        
        slide_formats = {".svs", ".tiff", ".ndpi", ".vms", ".vmu", ".scn", ".mrxs", ".bif"}  # Common slide file types
        slides = []

        #Scan the /slides directory
        for item in SLIDES_DIR.iterdir():
            if item.is_file() and item.suffix.lower() in slide_formats:
                slides.append(item.name)  # Normal slide files (.svs, .tiff)
            elif item.is_dir():
                # Handle folder-based slides like MRXS and DICOM
                if any(f.suffix.lower() in {".dat", ".mrxs"} for f in item.iterdir()):
                    slides.append(item.name)  # MRXS slide folder
                elif any(f.suffix.lower() in {".dcm"} for f in item.iterdir()):
                    slides.append(item.name)  # DICOM series folder

        if not slides:
            logger.warning("No slides found in /slides/")

        return templates.TemplateResponse("viewer.html", {"request": request, "slides": slides})

    # ---------- DeepZoom DZI Metadata ----------
    @application.get("/dzi/{slide_name}.dzi")
    async def get_dzi(slide_name: str):
        """Serve Deep Zoom Image (DZI) metadata for a given slide."""
        slide_path = SLIDES_DIR / slide_name

        logger.info(f"Checking DZI for: {slide_name}, Full path: {slide_path}")

        if not slide_path.exists():
            slide_path = SLIDES_DIR / (slide_name + ".svs")  # Try appending .svs

        if not slide_path.exists():
            logger.error(f"Slide not found: {slide_name} at {slide_path}")
            return JSONResponse(content={"error": "Slide not found"}, status_code=404)

        try:
            dzi = get_deepzoom(slide_path).get_dzi("jpeg")

            # Fix the Tile URL in DZI XML
            corrected_dzi = dzi.replace(f"{slide_name}_files/", f"tiles/{slide_name}/")
            logger.info(f"DZI successfully generated for: {slide_name}")
            return Response(content=corrected_dzi, media_type="application/xml")
        except Exception as e:
            logger.error(f"Error generating DZI for {slide_name}: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)


    # ---------- DeepZoom Tile Fetching ----------
    @application.get("/tiles/{slide_name}/{level}/{col}_{row}.jpeg")
    async def get_tile(slide_name: str, level: int, col: int, row: int):
        """Serve DeepZoom tiles for the viewer."""
        slide_path = SLIDES_DIR / slide_name

        if not slide_path.exists():
            logger.error(f"Slide not found: {slide_name}")
            return JSONResponse(content={"error": "Slide not found"}, status_code=404)

        try:
            dzi_gen = get_deepzoom(slide_path)
            tile = dzi_gen.get_tile(level, (col, row))
        except ValueError:
            logger.error(f"Invalid tile request: level={level}, col={col}, row={row}")
            return JSONResponse(content={"error": "Invalid tile coordinates"}, status_code=404)

        from io import BytesIO
        buffer = BytesIO()
        tile.save(buffer, format="JPEG")

        return Response(content=buffer.getvalue(), media_type="image/jpeg")
    
    @application.head("/tiles/{slide_name}/{level}/{col}_{row}.jpeg")
    async def get_tile_head(slide_name: str, level: int, col: int, row: int):
        """Handles HEAD requests for tiles (avoid fetching full image)."""
        slide_path = SLIDES_DIR / slide_name

        if not slide_path.exists():
            return JSONResponse(content={"error": "Slide not found"}, status_code=404)

        try:
            dzi_gen = get_deepzoom(slide_path)
            dzi_gen.get_tile(level, (col, row))  # Just check if tile exists
            return Response(status_code=200)
        except ValueError:
            return JSONResponse(content={"error": "Invalid tile coordinates"}, status_code=404)

    
    @application.get("/metadata/{slide_name}")
    async def get_metadata(slide_name: str, db: AsyncSession = Depends(async_get_db)):
        """
        Return metadata for a given slide (SVS, TIFF, DICOM, etc.),
        enriched with any associated Report data if a matching Slide exists.
        """
        slide_path = SLIDES_DIR / slide_name
        logger.info(f"Fetching metadata for: {slide_name}, Full path: {slide_path}")

        if not slide_path.exists():
            logger.error(f"Slide not found: {slide_name} at {slide_path}")
            return JSONResponse(content={"error": "Slide not found"}, status_code=404)

        try:
            # --- Default placeholder metadata ---
            metadata = {
                "macroscopy": "Placeholder macroscopy data",
                "microscopy": "Placeholder microscopy data",
                "clinical": "Placeholder clinical details",
                "diagnosis": "Placeholder diagnosis",
            }

            # --- Handle DICOM Folder ---
            if slide_path.is_dir():
                dicom_files = list(slide_path.glob("*.dcm"))
                if dicom_files:
                    dicom_sample = pydicom.dcmread(str(dicom_files[0]))
                    filtered_metadata = extract_filtered_metadata(dicom_sample)

                    width = int(dicom_sample.Columns) if hasattr(dicom_sample, "Columns") else 1024
                    height = int(dicom_sample.Rows) if hasattr(dicom_sample, "Rows") else 1024

                    metadata.update({
                        "levels": 1,
                        "tile_size": 256,
                        "level_dimensions": [(width, height)],
                        "max_width": width,
                        "max_height": height,
                        "metadata": filtered_metadata,
                    })

            # --- Handle SVS/Standard Slide ---
            elif slide_path.is_file():
                slide = openslide.OpenSlide(str(slide_path))
                dzi_gen = DeepZoomGenerator(slide, tile_size=256, overlap=1, limit_bounds=True)
                max_level = dzi_gen.level_count - 1
                max_size = dzi_gen.level_dimensions[max_level]

                metadata.update({
                    "levels": dzi_gen.level_count,
                    "tile_size": 256,
                    "level_dimensions": dzi_gen.level_dimensions,
                    "max_width": max_size[0],
                    "max_height": max_size[1],
                })

            # --- Attempt to resolve matching Slide in DB ---
            result = await db.execute(select(Slide).where(Slide.slide_name == slide_name))
            slide = result.scalar_one_or_none()

            if slide:
                report_stmt = (
                    select(Report)
                    .where(Report.linked_object_id == slide.id)
                    .where(Report.type == ReportType.SLIDE)
                    .options(selectinload(Report.property_values))
                )
                report_result = await db.execute(report_stmt)
                report = report_result.scalar_one_or_none()

                if report:
                    values = {pv.property_name: pv.value for pv in report.property_values}
                    logger.info(f"Report values found for slide {slide_name}: {values}")
                    metadata.update({
                        "macroscopy": values.get("Macroscopy", metadata["macroscopy"]),
                        "microscopy": values.get("Microscopy", metadata["microscopy"]),
                        "clinical": values.get("ClinicalDetails", metadata["clinical"]),
                        "diagnosis": values.get("Diagnosis", metadata["diagnosis"]),
                    })

            return JSONResponse(metadata)

        except Exception as e:
            logger.exception(f"Error fetching metadata for {slide_name}: {str(e)}")
            return JSONResponse(content={"error": f"Internal Server Error: {str(e)}"}, status_code=500)

    @application.get("/debug/files")
    async def debug_files():
        """Debugging route to list all files in the slides directory."""
        files = [f.name for f in SLIDES_DIR.glob("*")]
        return {"files_found": files}
    
    @application.get("/debug/check-file/{filename}")
    async def debug_check_file(filename: str):
        """Debugging route to check if FastAPI can access a specific file."""
        file_path = SLIDES_DIR / filename
        return {
            "exists": file_path.exists(),
            "is_file": file_path.is_file(),
            "absolute_path": str(file_path),
        }

    if isinstance(settings, ClientSideCacheSettings):
        application.add_middleware(ClientCacheMiddleware, max_age=settings.CLIENT_CACHE_MAX_AGE)

    if isinstance(settings, EnvironmentSettings):
        if settings.ENVIRONMENT != EnvironmentOption.PRODUCTION:
            docs_router = APIRouter()
            if settings.ENVIRONMENT != EnvironmentOption.LOCAL:
                docs_router = APIRouter(dependencies=[Depends(get_current_superuser)])

            @docs_router.get("/docs", include_in_schema=False)
            async def get_swagger_documentation() -> fastapi.responses.HTMLResponse:
                return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")

            @docs_router.get("/redoc", include_in_schema=False)
            async def get_redoc_documentation() -> fastapi.responses.HTMLResponse:
                return get_redoc_html(openapi_url="/openapi.json", title="docs")

            @docs_router.get("/openapi.json", include_in_schema=False)
            async def openapi() -> dict[str, Any]:
                out: dict = get_openapi(title=application.title, version=application.version, routes=application.routes)
                return out

            application.include_router(docs_router)

        return application
    

