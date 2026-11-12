from __future__ import annotations

import uuid
from datetime import date, datetime
from sqlalchemy import (
    Boolean,
    Date,
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

from app.core.database import Base, GUID, JSONType, SoftDeleteMixin, TimestampMixin


class ExamBody(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "exam_bodies"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[str] = mapped_column(String(64), default="India", nullable=False)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    exams: Mapped[list["Exam"]] = relationship("Exam", back_populates="exam_body")


class Exam(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "exams"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    exam_body_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exam_bodies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # board, competitive, govt
    class_level: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config_json: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)

    exam_body: Mapped["ExamBody"] = relationship("ExamBody", back_populates="exams")
    versions: Mapped[list["ExamVersion"]] = relationship("ExamVersion", back_populates="exam")
    exam_subjects: Mapped[list["ExamSubject"]] = relationship("ExamSubject", back_populates="exam")


class ExamVersion(Base, TimestampMixin):
    __tablename__ = "exam_versions"
    __table_args__ = (
        UniqueConstraint("exam_id", "academic_year", "version_code", name="uq_exam_year_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # e.g. "2024-25"
    version_code: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_marks: Mapped[int] = mapped_column(Integer, default=80, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    pattern_summary: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="versions")
    blueprints: Mapped[list["ExamBlueprint"]] = relationship(
        "ExamBlueprint", back_populates="exam_version"
    )


class Subject(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    stream: Mapped[str | None] = mapped_column(String(64), nullable=True)

    exam_subjects: Mapped[list["ExamSubject"]] = relationship("ExamSubject", back_populates="subject")


class ExamSubject(Base, TimestampMixin):
    __tablename__ = "exam_subjects"
    __table_args__ = (
        UniqueConstraint("exam_id", "subject_id", name="uq_exam_subject"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_code_in_exam: Mapped[str | None] = mapped_column(String(32), nullable=True)
    max_marks: Mapped[int] = mapped_column(Integer, default=80, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="exam_subjects")
    subject: Mapped["Subject"] = relationship("Subject", back_populates="exam_subjects")
    syllabus_versions: Mapped[list["SyllabusVersion"]] = relationship(
        "SyllabusVersion", back_populates="exam_subject"
    )


class SyllabusVersion(Base, TimestampMixin):
    __tablename__ = "syllabus_versions"
    __table_args__ = (
        UniqueConstraint("exam_subject_id", "version_tag", name="uq_syllabus_subject_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    exam_subject_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exam_subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_tag: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g., "2024-25-rationalised"
    academic_year: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    source_document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    exam_subject: Mapped["ExamSubject"] = relationship(
        "ExamSubject", back_populates="syllabus_versions"
    )
    topics: Mapped[list["SyllabusTopic"]] = relationship(
        "SyllabusTopic", back_populates="syllabus_version"
    )


class SyllabusTopic(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "syllabus_topics"
    __table_args__ = (
        UniqueConstraint("syllabus_version_id", "topic_code", name="uq_syllabus_topic_code"),
        Index("ix_syllabus_topics_chapter", "syllabus_version_id", "chapter_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    syllabus_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("syllabus_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_topic_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("syllabus_topics.id", ondelete="SET NULL"), nullable=True
    )
    topic_code: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_name: Mapped[str] = mapped_column(String(200), nullable=False)
    chapter_name: Mapped[str] = mapped_column(String(200), nullable=False)
    topic_name: Mapped[str] = mapped_column(String(250), nullable=False)
    official_weightage_marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    importance_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    keywords_json: Mapped[list[str] | None] = mapped_column(JSONType(), nullable=True)

    syllabus_version: Mapped["SyllabusVersion"] = relationship(
        "SyllabusVersion", back_populates="topics"
    )


class TopicPrerequisite(Base, TimestampMixin):
    __tablename__ = "topic_prerequisites"
    __table_args__ = (
        UniqueConstraint("topic_id", "prerequisite_topic_id", name="uq_topic_prereq"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("syllabus_topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prerequisite_topic_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("syllabus_topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    strength: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExamBlueprint(Base, TimestampMixin):
    __tablename__ = "exam_blueprints"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    exam_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exam_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exam_subject_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exam_subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_name: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "Section A"
    question_type: Mapped[str] = mapped_column(String(64), nullable=False)  # mcq, vsa, sa, la, case_study
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    marks_per_question: Mapped[float] = mapped_column(Float, nullable=False)
    total_section_marks: Mapped[float] = mapped_column(Float, nullable=False)
    is_competency_based: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    internal_choice_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)

    exam_version: Mapped["ExamVersion"] = relationship("ExamVersion", back_populates="blueprints")
