from sqlalchemy import Column, ForeignKey, String, Integer
from sqlalchemy.orm import relationship
import uuid
from sqlalchemy.dialects.postgresql import UUID
from ..core.db.database import Base


class TemplateGroup(Base):
    __tablename__ = 'template_groups'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey('profiles.id'), nullable=False)

    # Relationships
    profile = relationship("Profile", back_populates="template_groups")
    properties = relationship("TemplateProperty", back_populates="group", cascade="all, delete-orphan")
