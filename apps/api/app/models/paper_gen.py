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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID, JSONType, TimestampMixin, utcnow


class GeneratedPaper(Base, TimestampMixin):
    __tablename__ = "generated_papers"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    syllabus_version_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("syllabus_versions.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    total_marks: Mapped[int] = mapped_column(Integer, nullable=False)
    time_limit_minutes: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    language: Mapped[str] = mapped_column(String(32), default="English", nullable=False)
    blueprint_config_json: Mapped[dict] = mapped_column(JSONType(), nullable=False)
    solver_status: Mapped[str] = mapped_column(String(32), default="optimal", nullable=False)
    contains_ai_questions: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    paper_questions: Mapped[list["GeneratedPaperQuestion"]] = relationship(
        "GeneratedPaperQuestion", back_populates="generated_paper", cascade="all, delete-orphan"
    )
    attempts: Mapped[list["PaperAttempt"]] = relationship(
        "PaperAttempt", back_populates="generated_paper", cascade="all, delete-orphan"
    )


class GeneratedPaperQuestion(Base, TimestampMixin):
    __tablename__ = "generated_paper_questions"
    __table_args__ = (
        UniqueConstraint("generated_paper_id", "question_id", name="uq_gen_paper_question"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    generated_paper_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("generated_papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_name: Mapped[str] = mapped_column(String(64), default="Section A", nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated_marks: Mapped[float] = mapped_column(Float, nullable=False)

    generated_paper: Mapped["GeneratedPaper"] = relationship(
        "GeneratedPaper", back_populates="paper_questions"
    )


class PaperAttempt(Base, TimestampMixin):
    __tablename__ = "paper_attempts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    generated_paper_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("generated_papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="submitted", nullable=False)
    score_obtained: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    time_taken_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    answers_json: Mapped[dict] = mapped_column(JSONType(), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    generated_paper: Mapped["GeneratedPaper"] = relationship(
        "GeneratedPaper", back_populates="attempts"
    )
