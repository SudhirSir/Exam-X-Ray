from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.core_exam import SyllabusTopic
from app.models.student import (
    DiagnosticTest,
    StudentRecommendation,
    StudentTopicMastery,
    User,
)
from intelligence.vulnerability_scanner.engine import (
    ESTIMATE_DISCLAIMER,
    build_xray_report_from_test,
)

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/me/mastery")
def get_my_mastery(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(StudentTopicMastery)
        .filter(StudentTopicMastery.student_id == current_user.id)
        .order_by(StudentTopicMastery.mastery_score.asc())
        .all()
    )
    topics = {
        t.id: t
        for t in db.query(SyllabusTopic).filter(SyllabusTopic.id.in_([r.topic_id for r in rows])).all()
    } if rows else {}

    return {
        "has_data": len(rows) > 0,
        "disclaimer": ESTIMATE_DISCLAIMER,
        "items": [
            {
                "topic_id": str(r.topic_id),
                "chapter_name": topics[r.topic_id].chapter_name if r.topic_id in topics else "Unknown",
                "topic_name": topics[r.topic_id].topic_name if r.topic_id in topics else "Unknown",
                "mastery_score": r.mastery_score,
                "accuracy_pct": r.accuracy_pct,
                "attempts_count": r.attempts_count,
                "avg_time_seconds": r.avg_time_seconds,
                "vulnerability_index": r.vulnerability_index,
                "last_assessed_at": r.last_assessed_at.isoformat(),
            }
            for r in rows
        ],
    }


@router.get("/me/vulnerability")
def get_my_latest_vulnerability(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    latest = (
        db.query(DiagnosticTest)
        .filter(DiagnosticTest.student_id == current_user.id, DiagnosticTest.status == "evaluated")
        .order_by(DiagnosticTest.submitted_at.desc())
        .first()
    )
    if not latest:
        return {
            "has_data": False,
            "disclaimer": ESTIMATE_DISCLAIMER,
            "latest_report": None,
        }
    return {
        "has_data": True,
        "disclaimer": ESTIMATE_DISCLAIMER,
        "latest_report": build_xray_report_from_test(db, latest),
    }


@router.get("/me/recommendations")
def get_my_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recs = (
        db.query(StudentRecommendation)
        .filter(StudentRecommendation.student_id == current_user.id)
        .order_by(StudentRecommendation.priority_rank.asc())
        .all()
    )
    topics = {
        t.id: t
        for t in db.query(SyllabusTopic).filter(SyllabusTopic.id.in_([r.topic_id for r in recs])).all()
    } if recs else {}

    return {
        "has_data": len(recs) > 0,
        "items": [
            {
                "id": str(r.id),
                "topic_id": str(r.topic_id),
                "chapter_name": topics[r.topic_id].chapter_name if r.topic_id in topics else "General",
                "topic_name": topics[r.topic_id].topic_name if r.topic_id in topics else "General",
                "priority_rank": r.priority_rank,
                "priority_score": r.priority_score,
                "reason_explanation": r.reason_explanation,
                "estimated_hours": r.estimated_hours,
                "recommended_question_ids": r.recommended_question_ids_json or [],
                "status": r.status,
            }
            for r in recs
        ],
    }


@router.get("/me/progress")
def get_my_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tests = (
        db.query(DiagnosticTest)
        .filter(DiagnosticTest.student_id == current_user.id, DiagnosticTest.status == "evaluated")
        .order_by(DiagnosticTest.submitted_at.asc())
        .all()
    )
    return {
        "tests_completed": len(tests),
        "timeline": [
            {
                "test_id": str(t.id),
                "subject_id": str(t.subject_id),
                "submitted_at": t.submitted_at.isoformat() if t.submitted_at else None,
                "estimated_readiness_score": t.estimated_readiness_score or 0.0,
                "accuracy_pct": (t.summary_json or {}).get("accuracy_pct", 0.0),
            }
            for t in tests
        ],
    }
