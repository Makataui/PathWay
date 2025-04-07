from sqlalchemy import Column, ForeignKey, String, Integer
from sqlalchemy.orm import relationship
import uuid
from sqlalchemy.dialects.postgresql import UUID
from ..core.db.database import Base


class TemplateGroup(Base):
    __tablename__ = "template_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)

    version_id = Column(Integer, ForeignKey("template_versions.id"), nullable=False)

    version = relationship("TemplateVersion", back_populates="groups")
    properties = relationship("TemplateProperty", back_populates="group", cascade="all, delete-orphan")
    
    def __init__(self, name: str, version_id: int):
        self.name = name
        self.version_id = version_id