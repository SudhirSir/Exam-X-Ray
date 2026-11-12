from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.core_exam import Exam, Subject, SyllabusTopic
from app.models.operations import ProcessingRun
from app.models.question_intel import Question, QuestionPaper, QuestionTopic
from app.models.student import LearningActivityEvent
from spark.medallion import MedallionRunSummary, run_medallion_pipeline

logger = get_logger("medallion_runner")


def execute_medallion_from_db(
    db: Session,
    trigger_type: str = "manual",
    max_retries: int = 2,
    include_synthetic: bool = False,
) -> tuple[ProcessingRun, MedallionRunSummary | None]:
    """
    Pulls questions, topics, and pseudonymous student activity events from PostgreSQL/SQLite,
    executes the PySpark Bronze->Silver->Gold pipeline with retry handling,
    and records a ProcessingRun audit entry.
    """
    run = ProcessingRun(
        pipeline_name="exam_xray_medallion",
        layer="full_medallion",
        status="running",
        trigger_type=trigger_type,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    exams_by_id = {e.id: e for e in db.query(Exam).all()}
    subjects_by_id = {s.id: s for s in db.query(Subject).all()}
    topics_by_id = {t.id: t for t in db.query(SyllabusTopic).all()}
    papers_by_id = {p.id: p for p in db.query(QuestionPaper).filter(QuestionPaper.is_deleted.is_(False)).all()}

    q_query = db.query(Question).filter(Question.is_deleted.is_(False))
    if not include_synthetic:
        q_query = q_query.filter(Question.data_origin != "synthetic_dev")
    questions = q_query.all()

    primary_topic_map: dict[Any, Any] = {}
    for qt in db.query(QuestionTopic).filter(QuestionTopic.is_primary.is_(True)).all():
        primary_topic_map[qt.question_id] = qt.topic_id

    question_records: list[dict[str, Any]] = []
    for q in questions:
        paper = papers_by_id.get(q.question_paper_id)
        if not paper:
            continue
        exam = exams_by_id.get(paper.exam_id)
        subject = subjects_by_id.get(paper.subject_id)
        topic_id = primary_topic_map.get(q.id)
        topic = topics_by_id.get(topic_id) if topic_id else None

        question_records.append(
            {
                "question_id": str(q.id),
                "paper_id": str(paper.id),
                "exam_id": str(paper.exam_id),
                "exam_code": exam.code if exam else "UNKNOWN",
                "subject_id": str(paper.subject_id),
                "subject_code": subject.code if subject else "UNKNOWN",
                "syllabus_version_id": str(q.syllabus_version_id) if q.syllabus_version_id else None,
                "year": paper.year,
                "set_code": paper.set_code,
                "question_number": q.question_number,
                "section_name": q.section_name,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "marks": float(q.marks),
                "difficulty": q.difficulty,
                "is_competency_based": bool(q.is_competency_based),
                "chapter_name": topic.chapter_name if topic else None,
                "topic_id": str(topic.id) if topic else None,
                "topic_name": topic.topic_name if topic else None,
                "content_hash": q.content_hash,
                "verification_status": q.verification_status,
                "confidence_score": float(q.confidence_score),
                "data_origin": q.data_origin,
                "source_reference": q.source_reference or paper.title,
                "cluster_id": str(q.cluster_id) if q.cluster_id else None,
                "ingested_at": q.created_at.isoformat() if q.created_at else None,
            }
        )

    topic_records = [
        {
            "id": str(t.id),
            "chapter_name": t.chapter_name,
            "topic_name": t.topic_name,
            "official_weightage_marks": t.official_weightage_marks,
            "importance_score": t.importance_score,
        }
        for t in topics_by_id.values()
    ]

    events = db.query(LearningActivityEvent).all()
    activity_records = []
    for ev in events:
        payload = ev.payload_json or {}
        if ev.event_type != "question_answered":
            continue
        topic = topics_by_id.get(ev.topic_id) if ev.topic_id else None
        activity_records.append(
            {
                "event_id": str(ev.id),
                "analytics_pseudo_id": ev.analytics_pseudo_id,
                "exam_id": str(ev.exam_id) if ev.exam_id else None,
                "subject_id": str(ev.subject_id) if ev.subject_id else None,
                "topic_id": str(ev.topic_id) if ev.topic_id else None,
                "chapter_name": topic.chapter_name if topic else payload.get("chapter_name"),
                "topic_name": topic.topic_name if topic else payload.get("topic_name"),
                "is_correct": bool(payload.get("is_correct", False)),
                "time_spent_seconds": int(payload.get("time_spent_seconds", 60)),
                "difficulty": payload.get("difficulty", "medium"),
                "occurred_at": ev.occurred_at.isoformat(),
            }
        )

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            summary = run_medallion_pipeline(
                question_records=question_records,
                topic_records=topic_records,
                activity_records=activity_records,
            )
            run.status = "completed"
            run.records_in = summary.records_bronze
            run.records_out = summary.records_silver
            run.dq_passed = summary.dq_passed
            run.dq_report_json = summary.dq_report
            run.duration_seconds = summary.duration_seconds
            run.spark_app_id = summary.spark_app_id
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(run)
            return run, summary
        except Exception as exc:
            last_exc = exc
            logger.warning("medallion_attempt_failed", attempt=attempt + 1, error=str(exc))
            time.sleep(0.5 * (attempt + 1))

    run.status = "failed"
    run.dq_passed = False
    run.error_message = str(last_exc)
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run, None
