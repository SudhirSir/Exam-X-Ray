from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.analytics import (
    ExamDnaResponse,
    PatternChangeResponse,
    YearlyTrendComparisonResponse,
)
from intelligence.exam_dna.analyzer import build_exam_dna_report
from intelligence.pattern_change.engine import detect_pattern_changes
from intelligence.trend_detection.engine import compare_exam_years

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/exam-dna", response_model=ExamDnaResponse)
def get_exam_dna(
    exam_id: uuid.UUID = Query(...),
    subject_id: uuid.UUID = Query(...),
    year_from: int | None = Query(default=None),
    year_to: int | None = Query(default=None),
    include_synthetic: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    try:
        report = build_exam_dna_report(
            db=db,
            exam_id=exam_id,
            subject_id=subject_id,
            year_from=year_from,
            year_to=year_to,
            include_synthetic=include_synthetic,
        )
        return ExamDnaResponse(**report)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/topic-weightage")
def get_topic_weightage(
    exam_id: uuid.UUID = Query(...),
    subject_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
):
    try:
        report = build_exam_dna_report(db=db, exam_id=exam_id, subject_id=subject_id)
        return {
            "exam_id": str(exam_id),
            "subject_id": str(subject_id),
            "has_data": report["has_data"],
            "computation_source": report["computation_source"],
            "chapter_weightage": report["chapter_weightage"],
            "recurring_concepts": report["recurring_concepts"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/yearly-trends", response_model=YearlyTrendComparisonResponse)
def get_yearly_trends(
    exam_id: uuid.UUID = Query(...),
    subject_id: uuid.UUID = Query(...),
    year_a: int = Query(default=2023),
    year_b: int = Query(default=2024),
    db: Session = Depends(get_db),
):
    res = compare_exam_years(
        db=db,
        exam_id=exam_id,
        subject_id=subject_id,
        year_a=year_a,
        year_b=year_b,
    )
    return YearlyTrendComparisonResponse(**res)


@router.get("/pattern-changes", response_model=PatternChangeResponse)
def get_pattern_changes(
    exam_id: uuid.UUID = Query(...),
    subject_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
):
    res = detect_pattern_changes(db=db, exam_id=exam_id, subject_id=subject_id)
    return PatternChangeResponse(**res)
