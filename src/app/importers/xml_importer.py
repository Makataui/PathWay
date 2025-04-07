# app/importers/xml_importer.py

import logging
from xml.etree import ElementTree as ET
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from ..models import TemplateVersion, TemplateGroup, TemplateProperty
from ..core.db.database import async_get_db

logger = logging.getLogger(__name__)


async def import_xml_template(
    db: AsyncSession,
    xml_content: str,
    profile_id: UUID,
    version_label: str = "v1"
) -> TemplateVersion | None:
    """
    Import XML content and populate TemplateVersion, Groups, and Properties.
    """
    logger.info("Starting XML import process.")

    try:
        root = ET.fromstring(xml_content)
        logger.debug("XML parsed successfully.")
    except ET.ParseError as e:
        logger.error("Failed to parse XML: %s", str(e), exc_info=True)
        return None

    try:
        # Step 1: Create TemplateVersion
        version = TemplateVersion(
            profile_id=profile_id,
            version=version_label,
            version_is_active=True,  # Set active if this is the only one
        )
        db.add(version)
        await db.flush()  # Get version.id

        logger.info(f"Created TemplateVersion v{version.version} for profile {profile_id}")

        # Step 2: Parse groups (you can customize this XPath logic)
        for group_el in root.findall(".//Group"):
            group_name = group_el.attrib.get("name", "UnnamedGroup")
            group = TemplateGroup(name=group_name, version_id=version.id)
            db.add(group)
            await db.flush()

            logger.info(f"Added TemplateGroup: {group_name}")

            # Step 3: Parse properties under this group
            for prop_el in group_el.findall("Property"):
                name = prop_el.attrib.get("name")
                datatype = prop_el.attrib.get("type", "string")
                is_array = prop_el.attrib.get("array", "false").lower() == "true"
                is_object = prop_el.attrib.get("object", "false").lower() == "true"
                external_id = prop_el.attrib.get("id")
                json_path = prop_el.attrib.get("jsonPath")
                xml_path = prop_el.attrib.get("xmlPath")
                constraints = prop_el.attrib.get("constraints")  # JSON string or pipe-separated values

                property = TemplateProperty(
                    name=name,
                    datatype=datatype,
                    is_array=is_array,
                    is_object=is_object,
                    external_id=external_id,
                    json_path=json_path,
                    xml_path=xml_path,
                    constraints={"raw": constraints} if constraints else None,
                    group_id=group.id
                )

                logger.debug(f"Parsed property: {name} ({datatype})")
                db.add(property)

        await db.commit()
        logger.info("XML template import completed successfully.")
        return version

    except Exception as e:
        logger.exception("Error during XML template import: %s", str(e))
        await db.rollback()
        return None
