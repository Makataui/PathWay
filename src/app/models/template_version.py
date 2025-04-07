import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..core.db.database import Base

class TemplateVersion(Base):
    __tablename__ = "template_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String, nullable=False)  # e.g. "v1", "2025.01"
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)

    version_is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=func.now())

    profile = relationship("Profile", back_populates="template_versions")
    groups = relationship("TemplateGroup", back_populates="version", cascade="all, delete-orphan")
