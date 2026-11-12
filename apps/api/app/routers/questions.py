from __future__ import annotations

import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core_exam import SyllabusTopic
from app.models.question_intel import (
    Question,
    QuestionAnswer,
    QuestionOption,
    QuestionPaper,
    QuestionTopic,
)
from app.schemas.questions import (
    QuestionAnswerOut,
    QuestionOptionOut,
    QuestionOut,
    QuestionSearchResponse,
    SimilarQuestionItem,
    SimilarQuestionResponse,
)
from intelligence.question_similarity.engine import find_similar_questions

router = APIRouter(prefix="/questions", tags=["Questions"])


def serialize_question(
    db: Session,
    q: Question,
    paper: QuestionPaper | None = None,
    topic: SyllabusTopic | None = None,
) -> QuestionOut:
    if paper is None:
        paper = db.query(QuestionPaper).filter(QuestionPaper.id == q.question_paper_id).first()
    if topic is None:
        qt = (
            db.query(QuestionTopic)
            .filter(QuestionTopic.question_id == q.id, QuestionTopic.is_primary.is_(True))
            .first()
        )
        if qt:
            topic = db.query(SyllabusTopic).filter(SyllabusTopic.id == qt.topic_id).first()

    options = (
        db.query(QuestionOption)
        .filter(QuestionOption.question_id == q.id)
        .order_by(QuestionOption.option_label.asc())
        .all()
    )
    answers = db.query(QuestionAnswer).filter(QuestionAnswer.question_id == q.id).all()

    return QuestionOut(
        id=q.id,
        question_paper_id=q.question_paper_id,
        exam_id=paper.exam_id if paper else None,
        subject_id=paper.subject_id if paper else None,
        year=paper.year if paper else None,
        set_code=paper.set_code if paper else None,
        question_number=q.question_number,
        section_name=q.section_name,
        page_number=q.page_number,
        question_text=q.question_text,
        math_expressions=q.math_expressions_json or [],
        question_type=q.question_type,
        marks=float(q.marks),
        difficulty=q.difficulty,
        bloom_level=q.bloom_level,
        is_competency_based=q.is_competency_based,
        verification_status=q.verification_status,
        confidence_score=float(q.confidence_score),
        data_origin=q.data_origin,
        source_reference=q.source_reference or (paper.title if paper else None),
        chapter_name=topic.chapter_name if topic else None,
        topic_name=topic.topic_name if topic else None,
        options=[QuestionOptionOut.model_validate(o) for o in options],
        answers=[QuestionAnswerOut.model_validate(a) for a in answers],
    )


@router.get("", response_model=QuestionSearchResponse)
def list_questions(
    exam_id: uuid.UUID | None = Query(default=None),
    subject_id: uuid.UUID | None = Query(default=None),
    year: int | None = Query(default=None),
    question_type: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    verification_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    paper_q = db.query(QuestionPaper).filter(
        QuestionPaper.is_deleted.is_(False), QuestionPaper.data_origin != "synthetic_dev"
    )
    if exam_id:
        paper_q = paper_q.filter(QuestionPaper.exam_id == exam_id)
    if subject_id:
        paper_q = paper_q.filter(QuestionPaper.subject_id == subject_id)
    if year:
        paper_q = paper_q.filter(QuestionPaper.year == year)
    papers = {p.id: p for p in paper_q.all()}
    if not papers:
        return QuestionSearchResponse(total=0, page=page, page_size=page_size, items=[])

    q_query = db.query(Question).filter(
        Question.question_paper_id.in_(list(papers.keys())),
        Question.is_deleted.is_(False),
    )
    if question_type:
        q_query = q_query.filter(Question.question_type == question_type)
    if difficulty:
        q_query = q_query.filter(Question.difficulty == difficulty)
    if verification_status:
        q_query = q_query.filter(Question.verification_status == verification_status)

    total = q_query.count()
    items_raw = (
        q_query.order_by(Question.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return QuestionSearchResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[serialize_question(db, q, paper=papers.get(q.question_paper_id)) for q in items_raw],
    )


@router.get("/search", response_model=SimilarQuestionResponse)
def search_questions_semantic(
    q: str = Query(..., min_length=2),
    exam_id: uuid.UUID | None = Query(default=None),
    subject_id: uuid.UUID | None = Query(default=None),
    top_k: int = Query(default=10, ge=1, le=30),
    db: Session = Depends(get_db),
):
    matches = find_similar_questions(
        db=db,
        query_text=q,
        exam_id=exam_id,
        subject_id=subject_id,
        top_k=top_k,
    )
    results = [
        SimilarQuestionItem(
            question=serialize_question(db, m["question_obj"], paper=m["paper_obj"], topic=m["topic_obj"]),
            cosine_score=m["cosine_score"],
            metadata_score=m["metadata_score"],
            combined_confidence=m["combined_confidence"],
            relationship_type=m["relationship_type"],
            explanation=m["explanation"],
        )
        for m in matches
    ]
    return SimilarQuestionResponse(query_text=q, results=results)


@router.get("/similar", response_model=SimilarQuestionResponse)
def get_similar_questions(
    question_id: uuid.UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    exam_id: uuid.UUID | None = Query(default=None),
    subject_id: uuid.UUID | None = Query(default=None),
    top_k: int = Query(default=8, ge=1, le=25),
    db: Session = Depends(get_db),
):
    if not question_id and not q:
        raise HTTPException(status_code=400, detail="Provide either question_id or q query text.")
    matches = find_similar_questions(
        db=db,
        query_text=q,
        query_question_id=question_id,
        exam_id=exam_id,
        subject_id=subject_id,
        top_k=top_k,
    )
    results = [
        SimilarQuestionItem(
            question=serialize_question(db, m["question_obj"], paper=m["paper_obj"], topic=m["topic_obj"]),
            cosine_score=m["cosine_score"],
            metadata_score=m["metadata_score"],
            combined_confidence=m["combined_confidence"],
            relationship_type=m["relationship_type"],
            explanation=m["explanation"],
        )
        for m in matches
    ]
    return SimilarQuestionResponse(query_text=q, query_question_id=question_id, results=results)


@router.get("/{question_id}", response_model=QuestionOut)
def get_question(question_id: uuid.UUID, db: Session = Depends(get_db)):
    q = db.query(Question).filter(Question.id == question_id, Question.is_deleted.is_(False)).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found.")
    return serialize_question(db, q)
