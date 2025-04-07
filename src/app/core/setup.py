from collections.abc import AsyncGenerator, Callable
from contextlib import _AsyncGeneratorContextManager, asynccontextmanager
from typing import Any
from sqlalchemy.ext.asyncio.session import AsyncSession
from starlette.middleware.sessions import SessionMiddleware

import json
import pydicom
import anyio
import fastapi
import redis.asyncio as redis
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, FastAPI,Request, Response, Form
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.templating import Jinja2Templates
from pathlib import Path
from fastapi.responses import HTMLResponse, JSONResponse

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
from .db.database import Base, async_engine as engine
from .db.database import async_get_db
from .utils import cache, queue, rate_limit
from ..models import *

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

        if isinstance(settings, DatabaseSettings) and create_tables_on_start:
            await create_tables()

        if isinstance(settings, RedisCacheSettings):
            await create_redis_cache_pool()

        if isinstance(settings, RedisQueueSettings):
            await create_redis_queue_pool()

        if isinstance(settings, RedisRateLimiterSettings):
            await create_redis_rate_limit_pool()

        yield

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


    @application.get("/report", response_class=HTMLResponse)
    async def report_page(request: Request):
        return await render_template(request, "report.html")

    @application.get("/database", response_class=HTMLResponse)
    async def database_page(request: Request):
        return await render_template(request, "database.html")
    
    @application.get("/mapping", response_class=HTMLResponse)
    async def mapping_page(request: Request):
        return await render_template(request, "mapping.html")
    
    @application.get("/upload", response_class=HTMLResponse)
    async def upload_page(request: Request):
        return await render_template(request, "upload.html")

    @application.get("/upload_ds", response_class=HTMLResponse)
    async def upload_ds_page(request: Request):
        return await render_template(request, "upload_ds.html")
    
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
    async def get_metadata(slide_name: str):
        """Return metadata for a given slide (SVS, TIFF, DICOM, etc.)."""
        slide_path = SLIDES_DIR / slide_name
        logger.info(f"Fetching metadata for: {slide_name}, Full path: {slide_path}")

        if not slide_path.exists():
            logger.error(f"Slide not found: {slide_name} at {slide_path}")
            return JSONResponse(content={"error": "Slide not found"}, status_code=404)

        # **DICOM Handling (Folder-Based Slides)**
        if slide_path.is_dir():
            dicom_files = list(slide_path.glob("*.dcm"))
            if dicom_files:
                try:
                    dicom_sample = pydicom.dcmread(str(dicom_files[0]))

                    # **Filtered DICOM Metadata (No Base64)**
                    filtered_metadata = extract_filtered_metadata(dicom_sample)

                    # **Log Safe Metadata**
                    logger.info(f"Filtered DICOM metadata for {slide_name}: {json.dumps(filtered_metadata, indent=4)}")
                    patient_name = dicom_sample.PatientName if "PatientName" in dicom_sample else "Unknown"
                    patientID = dicom_sample.PatientID if "PatientID" in dicom_sample else "Unknown"
                    specimenDescriptionSequence = dicom_sample.SpecimenDescriptionSequence if "SpecimenDescriptionSequence" in dicom_sample else "Unknown"
                    acquisitionDate = dicom_sample.get("AcquisitionDate", "Unknown")

                    
                    logger.info(patient_name)
                    logger.info("Patient ID: " + patientID)
                    logger.info(specimenDescriptionSequence)
                    logger.info("Acquisition: " + acquisitionDate)

                    # **Extract Image Size**
                    width = int(dicom_sample.Columns) if hasattr(dicom_sample, "Columns") else 1024
                    height = int(dicom_sample.Rows) if hasattr(dicom_sample, "Rows") else 1024

                    metadata = {
                        "levels": 1,  # DICOM usually has only 1 level
                        "tile_size": 256,
                        "level_dimensions": [(width, height)],  # Fake single-level
                        "max_width": width,
                        "max_height": height,
                        "metadata": filtered_metadata,  # Only safe metadata
                    }

                    return JSONResponse(metadata)

                except Exception as e:
                    logger.error(f"Error reading DICOM metadata for {slide_name}: {e}", exc_info=True)
                    return JSONResponse(content={"error": str(e)}, status_code=500)

        # **Standard Slide Handling (.svs, .tiff, etc.)**
        try:
            slide = openslide.OpenSlide(str(slide_path))
            dzi_gen = openslide.deepzoom.DeepZoomGenerator(slide, tile_size=256, overlap=1, limit_bounds=True)

            # Use the **highest resolution level** for size
            max_level = dzi_gen.level_count - 1
            max_size = dzi_gen.level_dimensions[max_level]

            metadata = {
                "levels": dzi_gen.level_count,
                "tile_size": 256,
                "level_dimensions": dzi_gen.level_dimensions,
                "max_width": max_size[0],
                "max_height": max_size[1],
                "macroscopy": "Placeholder macroscopy data",
                "microscopy": "Placeholder microscopy data",
                "clinical": "Placeholder clinical details",
                "diagnosis": "Placeholder diagnosis"
            }
            logger.info(f"Metadata retrieved successfully for: {slide_name}")
            return JSONResponse(metadata)
        
        except Exception as e:
            logger.error(f"Error retrieving metadata for {slide_name} : {str(e)}")
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
    

