from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.core_exam import SyllabusTopic
from app.models.question_intel import QuestionOption, QuestionTopic
from app.models.student import DiagnosticTest, DiagnosticTestQuestion, User
from app.schemas.diagnostics import (
    DiagnosticQuestionItem,
    DiagnosticStartRequest,
    DiagnosticSubmitRequest,
    DiagnosticTestOut,
    XRayReportOut,
)
from intelligence.vulnerability_scanner.engine import (
    build_xray_report_from_test,
    evaluate_diagnostic_submission,
    select_diagnostic_questions,
)

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])


@router.get("/my-tests")
def list_my_diagnostics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tests = (
        db.query(DiagnosticTest)
        .filter(DiagnosticTest.student_id == current_user.id)
        .order_by(DiagnosticTest.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": str(t.id),
            "exam_id": str(t.exam_id),
            "subject_id": str(t.subject_id),
            "status": t.status,
            "estimated_readiness_score": t.estimated_readiness_score,
            "started_at": t.started_at.isoformat(),
            "submitted_at": t.submitted_at.isoformat() if t.submitted_at else None,
        }
        for t in tests
    ]


@router.post("/start", response_model=DiagnosticTestOut)
def start_diagnostic(
    payload: DiagnosticStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    selected = select_diagnostic_questions(
        db=db,
        exam_id=payload.exam_id,
        subject_id=payload.subject_id,
        question_count=payload.question_count,
        chapter_names=payload.chapter_names,
    )
    if not selected:
        raise HTTPException(
            status_code=404,
            detail="No verified diagnostic questions available for this exam and subject.",
        )

    test = DiagnosticTest(
        student_id=current_user.id,
        exam_id=payload.exam_id,
        subject_id=payload.subject_id,
        status="in_progress",
        time_limit_minutes=payload.time_limit_minutes,
    )
    db.add(test)
    db.flush()

    q_items: list[DiagnosticQuestionItem] = []
    for idx, q in enumerate(selected, start=1):
        exp_sec = 60 if q.marks <= 1 else (120 if q.marks <= 2 else 180)
        db.add(
            DiagnosticTestQuestion(
                diagnostic_test_id=test.id,
                question_id=q.id,
                order_index=idx,
                expected_time_seconds=exp_sec,
            )
        )
        qt = (
            db.query(QuestionTopic)
            .filter(QuestionTopic.question_id == q.id, QuestionTopic.is_primary.is_(True))
            .first()
        )
        topic = db.query(SyllabusTopic).filter(SyllabusTopic.id == qt.topic_id).first() if qt else None
        opts = (
            db.query(QuestionOption)
            .filter(QuestionOption.question_id == q.id)
            .order_by(QuestionOption.option_label.asc())
            .all()
        )
        q_items.append(
            DiagnosticQuestionItem(
                question_id=q.id,
                order_index=idx,
                question_text=q.question_text,
                question_type=q.question_type,
                marks=float(q.marks),
                difficulty=q.difficulty,
                chapter_name=topic.chapter_name if topic else None,
                topic_name=topic.topic_name if topic else None,
                expected_time_seconds=exp_sec,
                options=[{"option_label": o.option_label, "option_text": o.option_text} for o in opts],
            )
        )

    db.commit()
    db.refresh(test)
    return DiagnosticTestOut(
        id=test.id,
        exam_id=test.exam_id,
        subject_id=test.subject_id,
        status=test.status,
        time_limit_minutes=test.time_limit_minutes,
        started_at=test.started_at,
        questions=q_items,
    )


@router.post("/{diagnostic_id}/submit", response_model=XRayReportOut)
def submit_diagnostic(
    diagnostic_id: uuid.UUID,
    payload: DiagnosticSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == diagnostic_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Diagnostic test not found.")
    if test.student_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to submit this diagnostic test.")

    report = evaluate_diagnostic_submission(
        db=db,
        test=test,
        student=current_user,
        answers=[a.model_dump() for a in payload.answers],
    )
    return XRayReportOut(**report)


@router.get("/{diagnostic_id}/results", response_model=XRayReportOut)
def get_diagnostic_results(
    diagnostic_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == diagnostic_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Diagnostic test not found.")
    if test.student_id != current_user.id and current_user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Access denied.")
    if test.status != "evaluated":
        raise HTTPException(status_code=400, detail="Diagnostic test has not been submitted yet.")
    return XRayReportOut(**build_xray_report_from_test(db, test))
