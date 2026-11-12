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

from app.core.database import (
    Base,
    EmbeddingVector,
    GUID,
    JSONType,
    SoftDeleteMixin,
    TimestampMixin,
    utcnow,
)


class DataSource(Base, TimestampMixin):
    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)  # official_board, verified_archive, synthetic_dev
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(200), nullable=True)
    license_status: Mapped[str] = mapped_column(String(64), default="verified_permitted", nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    data_origin: Mapped[str] = mapped_column(
        String(32), default="verified_official", nullable=False, index=True
    )  # verified_official | synthetic_dev | ai_generated
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class QuestionPaper(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "question_papers"
    __table_args__ = (
        UniqueConstraint("exam_id", "subject_id", "year", "set_code", "data_origin", name="uq_paper_identity"),
        Index("ix_question_papers_exam_year", "exam_id", "subject_id", "year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    exam_version_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("exam_versions.id", ondelete="SET NULL"), nullable=True
    )
    syllabus_version_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("syllabus_versions.id", ondelete="SET NULL"), nullable=True
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    set_code: Mapped[str] = mapped_column(String(32), default="Main", nullable=False)
    paper_type: Mapped[str] = mapped_column(String(64), default="board_main", nullable=False)  # board_main, sample_paper, compartment
    language: Mapped[str] = mapped_column(String(32), default="English", nullable=False)
    total_marks: Mapped[int] = mapped_column(Integer, default=80, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    document_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    data_origin: Mapped[str] = mapped_column(String(32), default="verified_official", nullable=False, index=True)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    questions: Mapped[list["Question"]] = relationship("Question", back_populates="question_paper")


class QuestionCluster(Base, TimestampMixin):
    __tablename__ = "question_clusters"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("exams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cluster_label: Mapped[str] = mapped_column(String(200), nullable=False)
    pattern_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    years_appeared_json: Mapped[list[int] | None] = mapped_column(JSONType(), nullable=True)


class Question(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "questions"
    __table_args__ = (
        Index("ix_questions_paper_qnum", "question_paper_id", "question_number"),
        Index("ix_questions_type_diff", "question_type", "difficulty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    question_paper_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("question_papers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    syllabus_version_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("syllabus_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("question_clusters.id", ondelete="SET NULL"), nullable=True, index=True
    )
    question_number: Mapped[str] = mapped_column(String(32), nullable=False)
    section_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    math_expressions_json: Mapped[list[str] | None] = mapped_column(JSONType(), nullable=True)
    question_type: Mapped[str] = mapped_column(
        String(64), default="short_answer", nullable=False, index=True
    )  # mcq, assertion_reason, very_short, short_answer, long_answer, case_study
    marks: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    difficulty: Mapped[str] = mapped_column(
        String(32), default="medium", nullable=False, index=True
    )  # easy, medium, hard
    bloom_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_competency_based: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(32), default="English", nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False, index=True
    )  # pending, verified, rejected, ai_generated
    confidence_score: Mapped[float] = mapped_column(Float, default=0.9, nullable=False)
    data_origin: Mapped[str] = mapped_column(String(32), default="verified_official", nullable=False, index=True)
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)

    question_paper: Mapped["QuestionPaper"] = relationship("QuestionPaper", back_populates="questions")
    options: Mapped[list["QuestionOption"]] = relationship(
        "QuestionOption", back_populates="question", cascade="all, delete-orphan"
    )
    answers: Mapped[list["QuestionAnswer"]] = relationship(
        "QuestionAnswer", back_populates="question", cascade="all, delete-orphan"
    )
    topic_links: Mapped[list["QuestionTopic"]] = relationship(
        "QuestionTopic", back_populates="question", cascade="all, delete-orphan"
    )
    embedding: Mapped["QuestionEmbedding | None"] = relationship(
        "QuestionEmbedding", back_populates="question", uselist=False, cascade="all, delete-orphan"
    )


class QuestionOption(Base, TimestampMixin):
    __tablename__ = "question_options"
    __table_args__ = (
        UniqueConstraint("question_id", "option_label", name="uq_question_option_label"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    option_label: Mapped[str] = mapped_column(String(16), nullable=False)  # A, B, C, D
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    question: Mapped["Question"] = relationship("Question", back_populates="options")


class QuestionAnswer(Base, TimestampMixin):
    __tablename__ = "question_answers"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    marking_scheme_json: Mapped[list[dict] | None] = mapped_column(JSONType(), nullable=True)
    solution_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_official_key: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    question: Mapped["Question"] = relationship("Question", back_populates="answers")


class QuestionTopic(Base, TimestampMixin):
    __tablename__ = "question_topics"
    __table_args__ = (
        UniqueConstraint("question_id", "topic_id", name="uq_question_topic"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("syllabus_topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.9, nullable=False)
    assigned_by: Mapped[str] = mapped_column(String(32), default="nlp_classifier", nullable=False)

    question: Mapped["Question"] = relationship("Question", back_populates="topic_links")


class QuestionEmbedding(Base, TimestampMixin):
    __tablename__ = "question_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), default="1.0", nullable=False)
    embedding: Mapped[list[float]] = mapped_column(EmbeddingVector(384), nullable=False)

    question: Mapped["Question"] = relationship("Question", back_populates="embedding")


class QuestionSimilarity(Base, TimestampMixin):
    __tablename__ = "question_similarity"
    __table_args__ = (
        UniqueConstraint("source_question_id", "target_question_id", name="uq_question_sim_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    source_question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cosine_score: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    combined_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    relationship_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # exact_duplicate, paraphrase, same_concept, same_pattern, difficulty_variation
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), default="auto_flagged", nullable=False)


class ExtractionReview(Base, TimestampMixin):
    __tablename__ = "extraction_reviews"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    edits_json: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
