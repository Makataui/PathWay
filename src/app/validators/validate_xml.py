# app/validators/validate_xml.py

import logging
from xml.etree import ElementTree as ET
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from uuid import UUID

from ..models import TemplateVersion, TemplateGroup, TemplateProperty

logger = logging.getLogger(__name__)


async def validate_xml_structure(
    db: AsyncSession, xml_str: str, profile_id: UUID
) -> list[str]:
    """
    Validates the uploaded XML content against the active version for the profile.
    Returns a list of validation errors (empty list = success).
    """
    try:
        root = ET.fromstring(xml_str)
        logger.debug("Parsed uploaded XML successfully.")
    except ET.ParseError as e:
        logger.error("Uploaded XML parsing failed: %s", str(e))
        return [f"Failed to parse XML: {str(e)}"]

    stmt = (
        select(TemplateVersion)
        .where(TemplateVersion.profile_id == profile_id)
        .where(TemplateVersion.version_is_active == True)
        .options(
            selectinload(TemplateVersion.groups).selectinload(TemplateGroup.properties)
        )
    )
    result = await db.execute(stmt)
    version = result.scalars().first()

    if not version:
        logger.warning("No active template version found for profile %s", profile_id)
        return ["No active template version found for this profile."]

    errors = []

    # Build structured lookup from template model
    expected_structure = {
        group.name: {prop.name: prop for prop in group.properties}
        for group in version.groups
    }

    # Track uploaded group/property data
    uploaded_groups = {}

    for group_el in root.findall(".//Group"):
        group_name = group_el.attrib.get("name", "").strip()
        if not group_name:
            errors.append("Found a group with no 'name' attribute.")
            continue

        if group_name not in expected_structure:
            errors.append(f"Unexpected group: '{group_name}' not in template.")
            continue

        uploaded_props = {}
        for prop_el in group_el.findall("Property"):
            prop_name = prop_el.attrib.get("name", "").strip()
            if not prop_name:
                errors.append(f"Group '{group_name}' has a property with no name.")
                continue
            uploaded_props[prop_name] = prop_el.attrib

        uploaded_groups[group_name] = uploaded_props

    # Now validate against expected structure + constraints
    for group_name, expected_props in expected_structure.items():
        uploaded_props = uploaded_groups.get(group_name, {})

        for prop_name, prop_def in expected_props.items():
            constraints = prop_def.constraints or {}
            uploaded_attr = uploaded_props.get(prop_name)

            # Check for required
            if constraints.get("required", False) and not uploaded_attr:
                errors.append(f"Missing required property '{prop_name}' in group '{group_name}'.")

            # Check for allowed values if the property exists
            if uploaded_attr and "allowed_values" in constraints:
                actual_value = uploaded_attr.get("value")
                allowed = constraints["allowed_values"]
                if actual_value not in allowed:
                    errors.append(
                        f"Property '{prop_name}' in group '{group_name}' has value '{actual_value}', "
                        f"which is not in allowed list: {allowed}"
                    )

    return errors
