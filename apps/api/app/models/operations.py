from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, GUID, JSONType, TimestampMixin, utcnow


class IngestionJob(Base, TimestampMixin):
    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    set_code: Mapped[str] = mapped_column(String(32), default="Main", nullable=False)
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="queued", nullable=False, index=True
    )  # queued, extracting, spark_processing, completed, failed, duplicate
    pages_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    questions_extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    question_paper_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProcessingRun(Base, TimestampMixin):
    __tablename__ = "processing_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    pipeline_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    layer: Mapped[str] = mapped_column(String(32), nullable=False)  # bronze, silver, gold, full_medallion
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False, index=True)
    trigger_type: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    records_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dq_passed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    dq_report_json: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    spark_app_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details_json: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)


class ModelVersion(Base, TimestampMixin):
    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    model_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    framework: Mapped[str] = mapped_column(String(64), nullable=False)
    metrics_json: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
