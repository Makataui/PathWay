# models/report_property_value.py
from sqlalchemy import Column, ForeignKey, Integer, Float, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from ..core.db.database import Base

class ReportPropertyValue(Base):
    __tablename__ = "report_property_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(PG_UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("template_properties.id"), nullable=False)

    # Multi-type support (store only one)
    string_value = Column(Text, nullable=True)
    int_value = Column(Integer, nullable=True)
    float_value = Column(Float, nullable=True)
    bool_value = Column(Boolean, nullable=True)

    report = relationship("Report", back_populates="property_values")
    property = relationship("TemplateProperty")
