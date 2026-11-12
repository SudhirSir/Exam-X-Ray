from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.core_exam import Exam, Subject, SyllabusTopic
from app.models.paper_gen import GeneratedPaper, GeneratedPaperQuestion, PaperAttempt
from app.models.question_intel import (
    Question,
    QuestionAnswer,
    QuestionOption,
    QuestionTopic,
)
from app.models.student import User
from app.schemas.papers import (
    GeneratedPaperOut,
    GeneratedPaperQuestionOut,
    PaperAttemptOut,
    PaperAttemptRequest,
    PaperGenerateRequest,
)
from intelligence.paper_generator.engine import generate_optimized_paper, render_paper_pdf

router = APIRouter(prefix="/papers", tags=["Paper Generator"])


def _serialize_generated_paper(db: Session, paper: GeneratedPaper) -> GeneratedPaperOut:
    gpqs = (
        db.query(GeneratedPaperQuestion)
        .filter(GeneratedPaperQuestion.generated_paper_id == paper.id)
        .order_by(GeneratedPaperQuestion.order_index.asc())
        .all()
    )
    q_ids = [g.question_id for g in gpqs]
    questions = {q.id: q for q in db.query(Question).filter(Question.id.in_(q_ids)).all()} if q_ids else {}
    opts_map: dict[uuid.UUID, list[QuestionOption]] = {}
    for o in db.query(QuestionOption).filter(QuestionOption.question_id.in_(q_ids)).all():
        opts_map.setdefault(o.question_id, []).append(o)
    ans_map = {
        a.question_id: a for a in db.query(QuestionAnswer).filter(QuestionAnswer.question_id.in_(q_ids)).all()
    }
    q_topics = {
        qt.question_id: qt.topic_id
        for qt in db.query(QuestionTopic)
        .filter(QuestionTopic.question_id.in_(q_ids), QuestionTopic.is_primary.is_(True))
        .all()
    }
    topics = {
        t.id: t
        for t in db.query(SyllabusTopic).filter(SyllabusTopic.id.in_(list(q_topics.values()))).all()
    } if q_topics else {}

    out_questions: list[GeneratedPaperQuestionOut] = []
    actual_marks = 0.0
    for g in gpqs:
        q = questions.get(g.question_id)
        if not q:
            continue
        t = topics.get(q_topics.get(q.id))
        ans = ans_map.get(q.id)
        actual_marks += float(g.allocated_marks)
        out_questions.append(
            GeneratedPaperQuestionOut(
                question_id=q.id,
                section_name=g.section_name,
                order_index=g.order_index,
                allocated_marks=float(g.allocated_marks),
                question_text=q.question_text,
                question_type=q.question_type,
                difficulty=q.difficulty,
                chapter_name=t.chapter_name if t else "General",
                topic_name=t.topic_name if t else "General",
                options=[
                    {
                        "option_label": o.option_label,
                        "option_text": o.option_text,
                        "is_correct": o.is_correct,
                    }
                    for o in sorted(opts_map.get(q.id, []), key=lambda x: x.option_label)
                ],
                answer_text=ans.answer_text if ans else None,
                solution_steps=ans.solution_steps if ans else None,
                data_origin=q.data_origin,
            )
        )

    return GeneratedPaperOut(
        id=paper.id,
        exam_id=paper.exam_id,
        subject_id=paper.subject_id,
        title=paper.title,
        total_marks=paper.total_marks,
        actual_marks=round(actual_marks, 2),
        time_limit_minutes=paper.time_limit_minutes,
        language=paper.language,
        solver_status=paper.solver_status,
        contains_ai_questions=paper.contains_ai_questions,
        blueprint_config=paper.blueprint_config_json,
        created_at=paper.created_at,
        questions=out_questions,
    )


@router.post("/generate", response_model=GeneratedPaperOut)
def generate_paper(
    payload: PaperGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == payload.exam_id).first()
    subject = db.query(Subject).filter(Subject.id == payload.subject_id).first()
    if not exam or not subject:
        raise HTTPException(status_code=404, detail="Exam or subject not found.")

    try:
        solved = generate_optimized_paper(
            db=db,
            exam_id=payload.exam_id,
            subject_id=payload.subject_id,
            total_marks=payload.total_marks,
            question_count=payload.question_count,
            chapters=payload.chapters,
            question_types=payload.question_types,
            difficulty_distribution=payload.difficulty_distribution,
            language=payload.language,
            include_ai_generated=payload.include_ai_generated,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    title = payload.title or f"{exam.name} {subject.name} Practice Paper ({int(solved['actual_marks'])} Marks)"
    paper = GeneratedPaper(
        created_by_user_id=current_user.id,
        exam_id=payload.exam_id,
        subject_id=payload.subject_id,
        title=title,
        total_marks=payload.total_marks,
        time_limit_minutes=payload.time_limit_minutes,
        language=payload.language,
        blueprint_config_json=payload.model_dump(mode="json"),
        solver_status=solved["solver_status"],
        contains_ai_questions=solved["contains_ai_questions"],
    )
    db.add(paper)
    db.flush()

    for item in solved["items"]:
        db.add(
            GeneratedPaperQuestion(
                generated_paper_id=paper.id,
                question_id=item["question"].id,
                section_name=item["section_name"],
                order_index=item["order_index"],
                allocated_marks=item["allocated_marks"],
            )
        )
    db.commit()
    db.refresh(paper)
    return _serialize_generated_paper(db, paper)


@router.get("", response_model=list[GeneratedPaperOut])
def list_my_papers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    papers = (
        db.query(GeneratedPaper)
        .filter(GeneratedPaper.created_by_user_id == current_user.id)
        .order_by(GeneratedPaper.created_at.desc())
        .limit(25)
        .all()
    )
    return [_serialize_generated_paper(db, p) for p in papers]


@router.get("/{paper_id}", response_model=GeneratedPaperOut)
def get_generated_paper(
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    paper = db.query(GeneratedPaper).filter(GeneratedPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Generated paper not found.")
    return _serialize_generated_paper(db, paper)


@router.get("/{paper_id}/export")
def export_generated_paper(
    paper_id: uuid.UUID,
    format: str = Query(default="paper_pdf", pattern="^(paper_pdf|answer_key_pdf|json)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    paper = db.query(GeneratedPaper).filter(GeneratedPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Generated paper not found.")

    serialized = _serialize_generated_paper(db, paper)
    if format == "json":
        return serialized

    exam = db.query(Exam).filter(Exam.id == paper.exam_id).first()
    subject = db.query(Subject).filter(Subject.id == paper.subject_id).first()
    include_answers = format == "answer_key_pdf"
    pdf_bytes = render_paper_pdf(
        paper_title=paper.title,
        exam_name=exam.name if exam else "Exam",
        subject_name=subject.name if subject else "Subject",
        total_marks=serialized.actual_marks,
        duration_minutes=paper.time_limit_minutes,
        questions_data=[q.model_dump() for q in serialized.questions],
        include_answers=include_answers,
    )
    suffix = "answer_key" if include_answers else "question_paper"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="exam_xray_{suffix}_{str(paper.id)[:8]}.pdf"'
        },
    )


@router.post("/{paper_id}/attempt", response_model=PaperAttemptOut)
def attempt_generated_paper(
    paper_id: uuid.UUID,
    payload: PaperAttemptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    paper = db.query(GeneratedPaper).filter(GeneratedPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Generated paper not found.")

    serialized = _serialize_generated_paper(db, paper)
    score_obtained = 0.0
    max_score = 0.0
    feedback: list[dict] = []

    for q in serialized.questions:
        max_score += q.allocated_marks
        user_ans = (payload.answers.get(str(q.question_id)) or "").strip()
        is_correct = False
        if user_ans:
            corr_opt = next((o for o in q.options if o.get("is_correct")), None)
            if corr_opt and user_ans.lower() in {
                corr_opt["option_label"].lower(),
                corr_opt["option_text"].lower(),
            }:
                is_correct = True
            elif q.answer_text and user_ans.lower() in q.answer_text.lower():
                is_correct = True
        awarded = q.allocated_marks if is_correct else 0.0
        score_obtained += awarded
        feedback.append(
            {
                "question_id": str(q.question_id),
                "order_index": q.order_index,
                "submitted": user_ans,
                "expected": q.answer_text,
                "is_correct": is_correct,
                "marks_awarded": awarded,
                "max_marks": q.allocated_marks,
            }
        )

    now = datetime.now(timezone.utc)
    attempt = PaperAttempt(
        generated_paper_id=paper.id,
        user_id=current_user.id,
        status="submitted",
        score_obtained=score_obtained,
        max_score=max_score,
        time_taken_seconds=payload.time_taken_seconds,
        answers_json=payload.answers,
        submitted_at=now,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return PaperAttemptOut(
        id=attempt.id,
        generated_paper_id=paper.id,
        score_obtained=score_obtained,
        max_score=max_score,
        accuracy_pct=round(100.0 * score_obtained / max(max_score, 1.0), 1),
        time_taken_seconds=payload.time_taken_seconds,
        question_feedback=feedback,
        submitted_at=now,
    )
