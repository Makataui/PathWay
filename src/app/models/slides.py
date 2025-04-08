# app/models/slide.py

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from ..core.db.database import Base

class Slide(Base):
    __tablename__ = "slides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)  # Custom GUID
    slide_name = Column(String, nullable=False)
    slide_label = Column(String, nullable=True)
    slide_barcode = Column(String, nullable=True)
    case_identifier = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(self, slide_name, slide_label=None, slide_barcode=None, case_identifier=None):
        self.slide_name = slide_name
        self.slide_label = slide_label
        self.slide_barcode = slide_barcode
        self.case_identifier = case_identifier
        
    def __repr__(self):
        return f"<Slide(name={self.slide_name}, label={self.slide_label}, barcode={self.slide_barcode})>"
