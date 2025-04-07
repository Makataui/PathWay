# models/report.py
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from ..core.db.database import Base
from .enums import ReportType

class Report(Base):
    __tablename__ = "reports"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    linked_object_id = Column(PG_UUID(as_uuid=True), nullable=False)  # Points to Slide/Block/Specimen/Case
    type = Column(Enum(ReportType), nullable=False)
    report_text = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    property_values = relationship("ReportPropertyValue", back_populates="report", cascade="all, delete-orphan")
