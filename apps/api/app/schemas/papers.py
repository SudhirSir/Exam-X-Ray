from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class PaperGenerateRequest(BaseModel):
    exam_id: uuid.UUID
    subject_id: uuid.UUID
    title: str | None = None
    chapters: list[str] | None = None
    total_marks: int = Field(default=40, ge=5, le=100)
    question_count: int = Field(default=14, ge=3, le=50)
    question_types: list[str] | None = None
    difficulty_distribution: dict[str, float] = Field(
        default_factory=lambda: {"easy": 0.3, "medium": 0.5, "hard": 0.2}
    )
    time_limit_minutes: int = Field(default=90, ge=15, le=240)
    language: str = "English"
    include_ai_generated: bool = False


class GeneratedPaperQuestionOut(BaseModel):
    question_id: uuid.UUID
    section_name: str
    order_index: int
    allocated_marks: float
    question_text: str
    question_type: str
    difficulty: str
    chapter_name: str | None = None
    topic_name: str | None = None
    options: list[dict[str, Any]] = []
    answer_text: str | None = None
    solution_steps: str | None = None
    data_origin: str


class GeneratedPaperOut(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    subject_id: uuid.UUID
    title: str
    total_marks: int
    actual_marks: float
    time_limit_minutes: int
    language: str
    solver_status: str
    contains_ai_questions: bool
    blueprint_config: dict[str, Any]
    created_at: datetime
    questions: list[GeneratedPaperQuestionOut]


class PaperAttemptRequest(BaseModel):
    time_taken_seconds: int = Field(default=600, ge=0)
    answers: dict[str, str]


class PaperAttemptOut(BaseModel):
    id: uuid.UUID
    generated_paper_id: uuid.UUID
    score_obtained: float
    max_score: float
    accuracy_pct: float
    time_taken_seconds: int
    question_feedback: list[dict[str, Any]]
    submitted_at: datetime
