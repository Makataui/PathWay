from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from ..core.db.database import Base


class TemplateProperty(Base):
    __tablename__ = 'template_properties'

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('template_groups.id'), nullable=False)

    name = Column(String, nullable=False)                 # JSON property name
    external_id = Column(String)                          # XML node name or identifier
    datatype = Column(String, nullable=False)             # e.g., 'string', 'int', 'bool'
    is_array = Column(Boolean, default=False)             # whether the field is repeated
    is_object = Column(Boolean, default=False)            # for nested structures

    json_path = Column(String)                            # optional JSON path
    xml_path = Column(String)                             # optional XPath for XML

    constraints = Column(JSON, nullable=True)             # e.g., {"required": true, "min": 0}

    # Relationship
    group = relationship("TemplateGroup", back_populates="properties")
