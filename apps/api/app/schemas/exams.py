from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, Field


class ExamBodyOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    country: str
    website_url: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class SubjectOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    stream: str | None = None
    max_marks: int | None = None
    subject_code_in_exam: str | None = None


class ExamOut(BaseModel):
    id: uuid.UUID
    exam_body_id: uuid.UUID
    exam_body_code: str | None = None
    exam_body_name: str | None = None
    code: str
    name: str
    category: str
    class_level: str | None = None
    is_active: bool
    config_json: dict[str, Any] | None = None
    subjects: list[SubjectOut] = []


class ExamCreateRequest(BaseModel):
    exam_body_id: uuid.UUID
    code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=200)
    category: str = Field(min_length=2, max_length=64)
    class_level: str | None = None
    config_json: dict[str, Any] | None = None


class ExamVersionOut(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    academic_year: str
    version_code: str
    effective_from: date | None = None
    total_marks: int
    duration_minutes: int
    pattern_summary: dict[str, Any] | None = None
    is_current: bool

    model_config = {"from_attributes": True}


class SyllabusTopicOut(BaseModel):
    id: uuid.UUID
    topic_code: str
    unit_name: str
    chapter_name: str
    topic_name: str
    official_weightage_marks: float | None = None
    importance_score: float
    keywords: list[str] = []
