import logging
from xml.etree import ElementTree as ET
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from ..models import TemplateVersion, TemplateGroup, TemplateProperty

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
        version = TemplateVersion(
            profile_id=profile_id,
            version=version_label,
            version_is_active=True,
        )
        db.add(version)
        await db.flush()
        logger.info(f"Created TemplateVersion v{version.version} for profile {profile_id}")

        for group_el in root.findall(".//Group"):
            group_name = group_el.attrib.get("name", "UnnamedGroup")
            group = TemplateGroup(name=group_name, version_id=version.id)
            db.add(group)
            await db.flush()
            logger.info(f"Added TemplateGroup: {group_name}")

            for prop_el in group_el.findall("Property"):
                name = prop_el.attrib.get("name")
                datatype = prop_el.attrib.get("type", "string")
                is_array = prop_el.attrib.get("array", "false").lower() == "true"
                is_object = prop_el.attrib.get("object", "false").lower() == "true"
                external_id = prop_el.attrib.get("id")
                json_path = prop_el.attrib.get("jsonPath")
                xml_path = prop_el.attrib.get("xmlPath")
                fhir_mapping = prop_el.attrib.get("fhirMapping")
                hl7v2_path = prop_el.attrib.get("hl7v2Path")
                dicom_path = prop_el.attrib.get("dicomPath")
                raw_constraints = prop_el.attrib.get("constraints")

                # Parse constraints
                constraints = {}
                if raw_constraints:
                    for item in raw_constraints.split(";"):
                        if ":" not in item:
                            continue
                        key, value = item.split(":", 1)
                        if key == "allowed_values":
                            constraints["allowed_values"] = value.split("|")
                        elif key == "required":
                            constraints["required"] = value.lower() == "true"
                        else:
                            constraints[key] = value

                property = TemplateProperty(
                    name=name,
                    datatype=datatype,
                    is_array=is_array,
                    is_object=is_object,
                    external_id=external_id,
                    json_path=json_path,
                    xml_path=xml_path,
                    fhir_mapping=fhir_mapping,
                    hl7v2_path=hl7v2_path,
                    dicom_path = dicom_path,
                    constraints=constraints or None,
                    group_id=group.id
                )

                logger.debug(f"Parsed property: {name} ({datatype}), constraints={constraints}")
                db.add(property)

        await db.commit()
        logger.info("XML template import completed successfully.")
        return version
    #Catch exceptions
    except Exception as e:
        logger.exception("Error during XML template import: %s", str(e))
        await db.rollback()
        return None
