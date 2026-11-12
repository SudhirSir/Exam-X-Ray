from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class QuestionOptionOut(BaseModel):
    id: uuid.UUID
    option_label: str
    option_text: str
    is_correct: bool = False

    model_config = {"from_attributes": True}


class QuestionAnswerOut(BaseModel):
    id: uuid.UUID
    answer_text: str
    solution_steps: str | None = None
    marking_scheme_json: list[dict[str, Any]] | None = None
    is_official_key: bool

    model_config = {"from_attributes": True}


class QuestionOut(BaseModel):
    id: uuid.UUID
    question_paper_id: uuid.UUID
    exam_id: uuid.UUID | None = None
    subject_id: uuid.UUID | None = None
    year: int | None = None
    set_code: str | None = None
    question_number: str
    section_name: str | None = None
    page_number: int | None = None
    question_text: str
    math_expressions: list[str] = []
    question_type: str
    marks: float
    difficulty: str
    bloom_level: str | None = None
    is_competency_based: bool
    verification_status: str
    confidence_score: float
    data_origin: str
    source_reference: str | None = None
    chapter_name: str | None = None
    topic_name: str | None = None
    options: list[QuestionOptionOut] = []
    answers: list[QuestionAnswerOut] = []


class QuestionSearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[QuestionOut]


class SimilarQuestionItem(BaseModel):
    question: QuestionOut
    cosine_score: float
    metadata_score: float
    combined_confidence: float
    relationship_type: str
    explanation: str


class SimilarQuestionResponse(BaseModel):
    query_text: str | None = None
    query_question_id: uuid.UUID | None = None
    results: list[SimilarQuestionItem]


class QuestionVerifyRequest(BaseModel):
    verification_status: str = Field(pattern="^(verified|rejected|pending)$")
    question_text: str | None = None
    question_type: str | None = None
    marks: float | None = Field(default=None, gt=0, le=50)
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")
    topic_id: uuid.UUID | None = None
    notes: str | None = None
