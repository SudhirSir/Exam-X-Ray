from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.core_exam import SyllabusTopic
from app.models.paper_gen import GeneratedPaper
from app.models.student import DiagnosticTest, StudentTopicMastery, User

router = APIRouter(prefix="/teacher", tags=["Teacher"])


@router.get("/overview")
def get_teacher_overview(
    current_user: User = Depends(require_roles("teacher", "admin")),
    db: Session = Depends(get_db),
):
    students = db.query(User).filter(User.role == "student", User.is_deleted.is_(False)).all()
    evaluated_tests = db.query(DiagnosticTest).filter(DiagnosticTest.status == "evaluated").all()
    avg_readiness = (
        round(
            sum(t.estimated_readiness_score or 0.0 for t in evaluated_tests) / len(evaluated_tests),
            1,
        )
        if evaluated_tests
        else 0.0
    )

    mastery_rows = db.query(StudentTopicMastery).all()
    topics = {
        t.id: t
        for t in db.query(SyllabusTopic).filter(SyllabusTopic.id.in_([m.topic_id for m in mastery_rows])).all()
    } if mastery_rows else {}

    ch_scores: dict[str, list[float]] = defaultdict(list)
    for m in mastery_rows:
        t = topics.get(m.topic_id)
        if t:
            ch_scores[t.chapter_name].append(m.accuracy_pct)

    chapter_performance = [
        {
            "chapter_name": ch,
            "avg_accuracy_pct": round(sum(vals) / len(vals), 1),
            "student_samples": len(vals),
        }
        for ch, vals in sorted(ch_scores.items(), key=lambda x: sum(x[1]) / len(x[1]))
    ]

    papers_created = (
        db.query(GeneratedPaper)
        .filter(GeneratedPaper.created_by_user_id == current_user.id)
        .count()
    )

    return {
        "total_students": len(students),
        "diagnostics_completed": len(evaluated_tests),
        "class_avg_readiness_pct": avg_readiness,
        "teacher_papers_created": papers_created,
        "chapter_performance": chapter_performance,
    }


@router.get("/students-progress")
def get_students_progress(
    _user: User = Depends(require_roles("teacher", "admin")),
    db: Session = Depends(get_db),
):
    students = db.query(User).filter(User.role == "student", User.is_deleted.is_(False)).all()
    results = []
    for stu in students:
        tests = (
            db.query(DiagnosticTest)
            .filter(DiagnosticTest.student_id == stu.id, DiagnosticTest.status == "evaluated")
            .order_by(DiagnosticTest.submitted_at.desc())
            .all()
        )
        latest = tests[0] if tests else None
        results.append(
            {
                "student_pseudo_id": stu.analytics_pseudo_id,
                "student_name": stu.full_name,
                "diagnostics_taken": len(tests),
                "latest_readiness_estimate": latest.estimated_readiness_score if latest else None,
                "latest_accuracy_pct": (latest.summary_json or {}).get("accuracy_pct") if latest else None,
                "last_active": latest.submitted_at.isoformat() if latest and latest.submitted_at else None,
            }
        )
    return {"items": results}
