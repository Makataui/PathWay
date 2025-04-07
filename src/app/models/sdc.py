import uuid as uuid_pkg
from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, String, Text, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

from ..core.db.database import Base


class AnswerTypeEnum(PyEnum):
    FREE_TEXT = "Free Text"
    DROP_DOWN = "Dropdown"


class SDCForm(Base):
    __tablename__ = "sdc_forms"

    id: Mapped[int] = mapped_column(
        Integer, autoincrement=True, nullable=False, unique=True, primary_key=True, init=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(default_factory=uuid_pkg.uuid4, primary_key=True, unique=True)
    media_url: Mapped[str | None] = mapped_column(String, default=None)
    is_imported: Mapped[bool] = mapped_column(default=False, index=True)
    authority_name: Mapped[str | None] = mapped_column(Text, default=None)
    authority_id: Mapped[str | None] = mapped_column(Text, default=None)
    ontology_name: Mapped[str | None] = mapped_column(Text, default=None)
    sdc_questions = relationship("SDCQuestion", back_populates="sdc_form", cascade="all, delete-orphan")


class SDCQuestion(Base):
    __tablename__ = "sdc_questions"

    id: Mapped[int] = mapped_column(
        Integer, autoincrement=True, nullable=False, unique=True, primary_key=True, init=False
    )
    sdc_form_id: Mapped[int] = mapped_column(ForeignKey("sdc_forms.id"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[AnswerTypeEnum] = mapped_column(Enum(AnswerTypeEnum), nullable=False)
    unit_of_measurement: Mapped[str | None] = mapped_column(String(50), default=None)
    options: Mapped[str | None] = mapped_column(Text, default=None)
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(default_factory=uuid_pkg.uuid4, primary_key=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
    is_imported: Mapped[bool] = mapped_column(default=False, index=True)
    sdc_form = relationship("SDCForm", back_populates="sdc_questions")