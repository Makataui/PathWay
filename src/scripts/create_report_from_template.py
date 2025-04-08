import asyncio
from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, selectinload

from ..app.models import Slide, Report, ReportPropertyValue, TemplateVersion, TemplateProperty, TemplateGroup
from ..app.models.enums import ReportType
from ..app.core.db.database import local_session as async_session_maker # Adjust if your session setup differs
from ..app.core.logger import logging  # Use your project logger if set

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Hardcoded DSN for local testing (based on your .env)
DATABASE_URL = "postgresql+asyncpg://postgres:1234@localhost:5432/postgres"

# SQLAlchemy setup
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# --- Data to insert ---
sample_values = {
    "TumourType": "Superficial",
    "DepthOfInvasion": "Papillary dermis",
    "PerineuralInvasion": "No",
    "VascularInvasion": "No",
    "TumourThickness": "0.25",
    "PeripheralMargin": "2.61",
    "DeepMargin": "0.2",
    "ClinicalDetails": "left nasal bridge -bcc? short superior long lateral",
    "Macroscopy": "Left medial canthal incisional biopsy ?bcc JG/LG",
    "Microscopy": "Not provided",
    "Diagnosis": "BCC confirmed"
}

PROFILE_ID = UUID("27e40aa5-4688-4bb6-b0c3-d367e5df3b85")  # Replace with your real profile ID
SLIDE_NAME = "51_Caption.svs"  # Replace with your real slide name


async def create_report_from_template():
    async with AsyncSessionLocal() as session:
        try:
            # 🔍 Find slide
            slide_result = await session.execute(select(Slide).where(Slide.slide_name == SLIDE_NAME))
            slide = slide_result.scalar_one_or_none()

            if not slide:
                logger.error(f"Slide '{SLIDE_NAME}' not found in DB.")
                return

            # 🔍 Load template
            stmt = (
                select(TemplateVersion)
                .where(TemplateVersion.profile_id == PROFILE_ID)
                .where(TemplateVersion.version_is_active == True)
                .options(
                    selectinload(TemplateVersion.groups).selectinload(TemplateGroup.properties)
                )
            )
            version_result = await session.execute(stmt)
            template_version = version_result.scalars().first()

            if not template_version:
                logger.error(f"No active template version found for profile {PROFILE_ID}")
                return

            logger.info(f"Using template version: {template_version.version}")

            # Create report
            report = Report()
            report.linked_object_id = slide.id
            report.type = ReportType.SLIDE
            report.created_at = datetime.utcnow()
            report.report_text = "Auto-generated report"

            session.add(report)
            await session.flush()

            # 🧩 Map values to report properties
            all_properties = [p for g in template_version.groups for p in g.properties]
            for prop in all_properties:
                val = sample_values.get(prop.name)
                if val is None:
                    logger.warning(f"No sample value for property: {prop.name}")
                continue

            report_value = ReportPropertyValue()
            report_value.report_id = report.id
            report_value.property_id = prop.id  # ✅ Set the required FK
            report_value.property_name = prop.name
            report_value.value = val  # Assuming you have a hybrid `value` property that handles types

            session.add(report_value)


            await session.commit()
            logger.info(f"Report created for slide: {slide.slide_name}")

        except Exception as e:
            logger.exception("Failed to create report from template")
            await session.rollback()


if __name__ == "__main__":
    asyncio.run(create_report_from_template())