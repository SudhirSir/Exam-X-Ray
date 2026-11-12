from __future__ import annotations

import uuid
from typing import Any
from pydantic import BaseModel


class ChapterWeightageItem(BaseModel):
    chapter_name: str
    total_marks: float
    question_count: int
    weightage_pct: float
    avg_difficulty_score: float


class QuestionTypeItem(BaseModel):
    question_type: str
    question_count: int
    total_marks: float
    share_pct: float


class DifficultyDistItem(BaseModel):
    difficulty: str
    question_count: int
    total_marks: float
    share_pct: float


class YearlyMetricItem(BaseModel):
    year: int
    papers_count: int
    questions_count: int
    total_marks: float
    competency_share_pct: float
    avg_difficulty_score: float


class RecurringConceptItem(BaseModel):
    topic_id: str | None = None
    chapter_name: str
    topic_name: str
    years_appeared: list[int]
    occurrence_count: int
    total_marks_across_years: float
    source_references: list[str]


class SourceCoverageItem(BaseModel):
    paper_id: str
    title: str
    year: int
    set_code: str
    data_origin: str
    is_verified: bool
    extraction_confidence: float
    source_url: str | None = None
    question_count: int


class ExamDnaResponse(BaseModel):
    exam_id: uuid.UUID
    exam_name: str
    subject_id: uuid.UUID
    subject_name: str
    year_from: int | None = None
    year_to: int | None = None
    has_data: bool
    total_analyzed_papers: int
    total_verified_questions: int
    total_questions_all_origins: int
    data_confidence_score: float
    computation_source: str  # gold_spark_delta | live_sql_fallback
    chapter_weightage: list[ChapterWeightageItem]
    question_type_distribution: list[QuestionTypeItem]
    difficulty_distribution: list[DifficultyDistItem]
    yearly_trends: list[YearlyMetricItem]
    recurring_concepts: list[RecurringConceptItem]
    sources: list[SourceCoverageItem]
    disclaimer: str


class YearlyTrendComparisonResponse(BaseModel):
    exam_id: uuid.UUID
    subject_id: uuid.UUID
    year_a: int
    year_b: int
    has_data: bool
    chapter_shifts: list[dict[str, Any]]
    question_type_shifts: list[dict[str, Any]]
    difficulty_shifts: list[dict[str, Any]]
    competency_shift_pct: float
    yearly_series: list[YearlyMetricItem]
    disclaimer: str


class PatternChangeItem(BaseModel):
    from_year: str
    to_year: str
    change_category: str
    summary: str
    previous_value: Any
    current_value: Any
    impact_on_preparation: str
    supporting_sources: list[str]


class PatternChangeResponse(BaseModel):
    exam_id: uuid.UUID
    subject_id: uuid.UUID
    previous_version: dict[str, Any] | None = None
    current_version: dict[str, Any] | None = None
    changes: list[PatternChangeItem]
    disclaimer: str
