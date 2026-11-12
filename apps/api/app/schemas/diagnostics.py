from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class DiagnosticStartRequest(BaseModel):
    exam_id: uuid.UUID
    subject_id: uuid.UUID
    question_count: int = Field(default=10, ge=5, le=40)
    time_limit_minutes: int | None = Field(default=25, ge=5, le=180)
    chapter_names: list[str] | None = None


class DiagnosticQuestionItem(BaseModel):
    question_id: uuid.UUID
    order_index: int
    question_text: str
    question_type: str
    marks: float
    difficulty: str
    chapter_name: str | None = None
    topic_name: str | None = None
    expected_time_seconds: int
    options: list[dict[str, Any]] = []


class DiagnosticTestOut(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    subject_id: uuid.UUID
    status: str
    time_limit_minutes: int | None = None
    started_at: datetime
    questions: list[DiagnosticQuestionItem]


class DiagnosticAnswerItem(BaseModel):
    question_id: uuid.UUID
    submitted_answer: str | None = None
    time_spent_seconds: int = Field(default=60, ge=0, le=3600)
    confidence_self_rating: int | None = Field(default=None, ge=1, le=5)


class DiagnosticSubmitRequest(BaseModel):
    answers: list[DiagnosticAnswerItem]


class TopicVulnerabilityItem(BaseModel):
    topic_id: uuid.UUID
    chapter_name: str
    topic_name: str
    accuracy_pct: float
    mastery_score: float
    avg_time_seconds: float
    vulnerability_index: float
    historical_weightage_marks: float
    prerequisite_gaps: list[str]
    mistake_patterns: list[str]


class RecommendationItem(BaseModel):
    topic_id: uuid.UUID
    chapter_name: str
    topic_name: str
    priority_rank: int
    priority_score: float
    reason_explanation: str
    estimated_hours: float
    recommended_question_ids: list[uuid.UUID]


class XRayReportOut(BaseModel):
    diagnostic_test_id: uuid.UUID
    exam_id: uuid.UUID
    subject_id: uuid.UUID
    status: str
    submitted_at: datetime | None = None
    estimated_readiness_score: float
    readiness_label: str
    estimate_disclaimer: str
    total_questions: int
    correct_count: int
    accuracy_pct: float
    avg_time_per_question_seconds: float
    difficulty_performance: list[dict[str, Any]]
    question_type_performance: list[dict[str, Any]]
    mistake_breakdown: list[dict[str, Any]]
    chapter_heatmap: list[dict[str, Any]]
    topic_vulnerabilities: list[TopicVulnerabilityItem]
    recommendations: list[RecommendationItem]
    next_practice_session: dict[str, Any] | None = None
    historical_progress: list[dict[str, Any]] = []
