# services/api/src/db/models.py
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConfigType(str, enum.Enum):
    VLESS = "vless"
    VMESS = "vmess"


class TestKind(str, enum.Enum):
    PERFORMANCE = "performance"
    STABILITY = "stability"
    COMPLIANCE = "compliance"
    SECURITY_BASIC = "security_basic"
    SECURITY_ADV = "security_adv"  # gated, requires explicit consent


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.USER, nullable=False)

    tasks: Mapped[list["Task"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    consents: Mapped[list["ConsentLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_users_created_at", "created_at"),)


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.PENDING, index=True)
    config_type: Mapped[ConfigType] = mapped_column(SAEnum(ConfigType), nullable=False)

    # raw config string as provided by user (validated later by worker)
    config_raw: Mapped[str] = mapped_column(Text, nullable=False)

    # List of requested tests, stored as JSON array of strings (TestKind values)
    tests: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # consent flags for advanced tests
    consent_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_granted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Optional labels/metadata
    label: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    user: Mapped["User"] = relationship(back_populates="tasks")
    result: Mapped[Optional["Result"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", uselist=False
    )
    report: Mapped[Optional["Report"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        Index("ix_tasks_user_created", "user_id", "created_at"),
        CheckConstraint("jsonb_typeof(tests) = 'array'", name="ck_tasks_tests_array"),
    )


class Result(Base, TimestampMixin):
    __tablename__ = "results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, index=True
    )

    # compact computed score (0..100) for user-facing summary
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # structured summaries and raw metrics/artifacts
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    task: Mapped["Task"] = relationship(back_populates="result")

    __table_args__ = (Index("ix_results_created_at", "created_at"),)


class ConsentLog(Base, TimestampMixin):
    __tablename__ = "consent_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)

    text: Mapped[str] = mapped_column(String(255), nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="consents")

    __table_args__ = (
        UniqueConstraint("user_id", "task_id", name="uq_consent_user_task"),
        Index("ix_consent_created_at", "created_at"),
    )


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, index=True
    )

    # artifact locations (path or URL) – produced by Reports service
    html_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    storage_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    task: Mapped["Task"] = relationship(back_populates="report")

    __table_args__ = (Index("ix_reports_created_at", "created_at"),)
