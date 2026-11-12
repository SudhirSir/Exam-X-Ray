from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID, JSONType, SoftDeleteMixin, TimestampMixin, utcnow


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[str] = mapped_column(
        String(32), default="student", nullable=False, index=True
    )  # student, teacher, admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Pseudonymous ID used exclusively in PySpark/Gold analytical datasets (no PII)
    analytics_pseudo_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, default=lambda: f"stu_{uuid.uuid4().hex[:16]}"
    )
    is_minor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    guardian_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guardian_consent_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    exam_profiles: Mapped[list["StudentExamProfile"]] = relationship(
        "StudentExamProfile", back_populates="user"
    )


class StudentExamProfile(Base, TimestampMixin):
    __tablename__ = "student_exam_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "exam_id", name="uq_student_exam_profile"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_year: Mapped[int] = mapped_column(Integer, default=2026, nullable=False)
    daily_study_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(32), default="English", nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="exam_profiles")


class DiagnosticTest(Base, TimestampMixin):
    __tablename__ = "diagnostic_tests"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), default="in_progress", nullable=False, index=True
    )  # in_progress, submitted, evaluated
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_readiness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary_json: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)

    test_questions: Mapped[list["DiagnosticTestQuestion"]] = relationship(
        "DiagnosticTestQuestion", back_populates="diagnostic_test", cascade="all, delete-orphan"
    )
    responses: Mapped[list["StudentResponse"]] = relationship(
        "StudentResponse", back_populates="diagnostic_test", cascade="all, delete-orphan"
    )


class DiagnosticTestQuestion(Base, TimestampMixin):
    __tablename__ = "diagnostic_test_questions"
    __table_args__ = (
        UniqueConstraint("diagnostic_test_id", "question_id", name="uq_diag_test_question"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    diagnostic_test_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("diagnostic_tests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_time_seconds: Mapped[int] = mapped_column(Integer, default=90, nullable=False)

    diagnostic_test: Mapped["DiagnosticTest"] = relationship(
        "DiagnosticTest", back_populates="test_questions"
    )


class StudentResponse(Base, TimestampMixin):
    __tablename__ = "student_responses"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    diagnostic_test_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("diagnostic_tests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submitted_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    marks_awarded: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mistake_type: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # conceptual_gap, calculation_error, time_pressure, skipped, misread_question

    diagnostic_test: Mapped["DiagnosticTest"] = relationship(
        "DiagnosticTest", back_populates="responses"
    )


class StudentTopicMastery(Base, TimestampMixin):
    __tablename__ = "student_topic_mastery"
    __table_args__ = (
        UniqueConstraint("student_id", "topic_id", name="uq_student_topic_mastery"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("syllabus_topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0.0 - 1.0 estimate
    accuracy_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_time_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    vulnerability_index: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class StudentRecommendation(Base, TimestampMixin):
    __tablename__ = "student_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("syllabus_topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    priority_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    reason_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_question_ids_json: Mapped[list[str] | None] = mapped_column(JSONType(), nullable=True)
    estimated_hours: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class LearningActivityEvent(Base, TimestampMixin):
    __tablename__ = "learning_activity_events"
    __table_args__ = (
        Index("ix_learning_events_pseudo_ts", "analytics_pseudo_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analytics_pseudo_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    exam_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    subject_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    topic_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
