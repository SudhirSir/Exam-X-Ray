from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.core_exam import (
    Exam,
    ExamBody,
    ExamSubject,
    ExamVersion,
    Subject,
    SyllabusTopic,
    SyllabusVersion,
)
from app.schemas.exams import (
    ExamBodyOut,
    ExamCreateRequest,
    ExamOut,
    ExamVersionOut,
    SubjectOut,
    SyllabusTopicOut,
)

router = APIRouter(prefix="/exams", tags=["Examinations"])


def _serialize_exam(db: Session, exam: Exam) -> ExamOut:
    body = db.query(ExamBody).filter(ExamBody.id == exam.exam_body_id).first()
    es_rows = db.query(ExamSubject).filter(ExamSubject.exam_id == exam.id).all()
    subj_map = {
        s.id: s
        for s in db.query(Subject).filter(Subject.id.in_([es.subject_id for es in es_rows])).all()
    } if es_rows else {}

    subjects_out: list[SubjectOut] = []
    for es in es_rows:
        s = subj_map.get(es.subject_id)
        if s and not s.is_deleted:
            subjects_out.append(
                SubjectOut(
                    id=s.id,
                    code=s.code,
                    name=s.name,
                    stream=s.stream,
                    max_marks=es.max_marks,
                    subject_code_in_exam=es.subject_code_in_exam,
                )
            )

    return ExamOut(
        id=exam.id,
        exam_body_id=exam.exam_body_id,
        exam_body_code=body.code if body else None,
        exam_body_name=body.name if body else None,
        code=exam.code,
        name=exam.name,
        category=exam.category,
        class_level=exam.class_level,
        is_active=exam.is_active,
        config_json=exam.config_json,
        subjects=subjects_out,
    )


@router.get("/bodies", response_model=list[ExamBodyOut])
def list_exam_bodies(db: Session = Depends(get_db)):
    bodies = db.query(ExamBody).filter(ExamBody.is_deleted.is_(False)).order_by(ExamBody.name).all()
    return [ExamBodyOut.model_validate(b) for b in bodies]


@router.get("", response_model=list[ExamOut])
def list_exams(
    category: str | None = Query(default=None),
    class_level: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(Exam).filter(Exam.is_deleted.is_(False))
    if category:
        q = q.filter(Exam.category == category)
    if class_level:
        q = q.filter(Exam.class_level == class_level)
    exams = q.order_by(Exam.name.asc()).all()
    return [_serialize_exam(db, e) for e in exams]


@router.post("", response_model=ExamOut, status_code=status.HTTP_201_CREATED)
def create_exam(
    payload: ExamCreateRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_roles("admin")),
):
    if db.query(Exam).filter(Exam.code == payload.code).first():
        raise HTTPException(status_code=409, detail="Exam code already exists.")
    exam = Exam(
        exam_body_id=payload.exam_body_id,
        code=payload.code,
        name=payload.name,
        category=payload.category,
        class_level=payload.class_level,
        config_json=payload.config_json,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return _serialize_exam(db, exam)


@router.get("/{exam_id}", response_model=ExamOut)
def get_exam(exam_id: uuid.UUID, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.is_deleted.is_(False)).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found.")
    return _serialize_exam(db, exam)


@router.get("/{exam_id}/subjects", response_model=list[SubjectOut])
def get_exam_subjects(exam_id: uuid.UUID, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.is_deleted.is_(False)).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found.")
    return _serialize_exam(db, exam).subjects


@router.get("/{exam_id}/versions", response_model=list[ExamVersionOut])
def get_exam_versions(exam_id: uuid.UUID, db: Session = Depends(get_db)):
    versions = (
        db.query(ExamVersion)
        .filter(ExamVersion.exam_id == exam_id)
        .order_by(ExamVersion.academic_year.asc())
        .all()
    )
    return [ExamVersionOut.model_validate(v) for v in versions]


@router.get("/{exam_id}/topics", response_model=list[SyllabusTopicOut])
def get_exam_topics(
    exam_id: uuid.UUID,
    subject_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
):
    es = (
        db.query(ExamSubject)
        .filter(ExamSubject.exam_id == exam_id, ExamSubject.subject_id == subject_id)
        .first()
    )
    if not es:
        return []
    sv = (
        db.query(SyllabusVersion)
        .filter(SyllabusVersion.exam_subject_id == es.id, SyllabusVersion.is_active.is_(True))
        .order_by(SyllabusVersion.academic_year.desc())
        .first()
    )
    if not sv:
        return []
    topics = (
        db.query(SyllabusTopic)
        .filter(SyllabusTopic.syllabus_version_id == sv.id, SyllabusTopic.is_deleted.is_(False))
        .order_by(SyllabusTopic.chapter_name.asc(), SyllabusTopic.topic_name.asc())
        .all()
    )
    return [
        SyllabusTopicOut(
            id=t.id,
            topic_code=t.topic_code,
            unit_name=t.unit_name,
            chapter_name=t.chapter_name,
            topic_name=t.topic_name,
            official_weightage_marks=t.official_weightage_marks,
            importance_score=t.importance_score,
            keywords=t.keywords_json or [],
        )
        for t in topics
    ]
