from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles
from app.models.core_exam import Exam, Subject
from app.models.operations import AuditLog, IngestionJob, ProcessingRun
from app.models.question_intel import (
    DataSource,
    ExtractionReview,
    Question,
    QuestionAnswer,
    QuestionOption,
    QuestionPaper,
    QuestionTopic,
)
from app.models.student import User
from app.schemas.admin import IngestionJobOut, ProcessingRunOut
from app.schemas.questions import QuestionVerifyRequest
from ingestion.pdf_extractor import extract_pdf_questions
from ingestion.storage import DocumentStorageService, compute_sha256, validate_pdf_bytes
from intelligence.question_similarity.engine import (
    auto_classify_question_topic,
    cluster_questions_for_subject,
    ensure_question_embeddings,
)
from pipelines.medallion_runner import execute_medallion_from_db

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.post("/documents/upload")
async def upload_exam_document(
    exam_id: uuid.UUID = Form(...),
    subject_id: uuid.UUID = Form(...),
    year: int = Form(..., ge=2000, le=2035),
    set_code: str = Form(default="Main"),
    paper_type: str = Form(default="board_main"),
    language: str = Form(default="English"),
    source_url: str | None = Form(default=None),
    data_origin: str = Form(default="verified_official"),
    auto_verify: bool = Form(default=False),
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not exam or not subject:
        raise HTTPException(status_code=404, detail="Exam or subject not found.")

    content = await file.read()
    try:
        validate_pdf_bytes(file.filename or "paper.pdf", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    file_hash = compute_sha256(content)
    existing_paper = db.query(QuestionPaper).filter(QuestionPaper.document_hash == file_hash).first()
    if existing_paper:
        dup_job = IngestionJob(
            uploaded_by_user_id=current_user.id,
            exam_id=exam_id,
            subject_id=subject_id,
            year=year,
            set_code=set_code,
            file_name=file.filename or "paper.pdf",
            file_hash=file_hash,
            storage_key=existing_paper.storage_key or "",
            source_url=source_url,
            status="duplicate",
            question_paper_id=existing_paper.id,
            error_message="Exact SHA-256 duplicate of an already ingested paper.",
            completed_at=datetime.now(timezone.utc),
        )
        db.add(dup_job)
        db.commit()
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate PDF detected (SHA-256 {file_hash[:12]}... matches '{existing_paper.title}').",
        )

    storage = DocumentStorageService()
    storage_key = storage.save_document(file.filename or "paper.pdf", content, file_hash)

    job = IngestionJob(
        uploaded_by_user_id=current_user.id,
        exam_id=exam_id,
        subject_id=subject_id,
        year=year,
        set_code=set_code,
        file_name=file.filename or "paper.pdf",
        file_hash=file_hash,
        storage_key=storage_key,
        source_url=source_url,
        status="extracting",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        extraction = extract_pdf_questions(content)
        source = DataSource(
            name=f"{exam.name} {subject.name} {year} ({set_code})",
            source_type="official_board" if data_origin == "verified_official" else "uploaded_pdf",
            source_url=source_url,
            is_verified=auto_verify,
            data_origin=data_origin,
        )
        db.add(source)
        db.flush()

        # Disambiguate set_code if (exam_id, subject_id, year, set_code, data_origin) already exists
        existing_same_slot = (
            db.query(QuestionPaper)
            .filter(
                QuestionPaper.exam_id == exam_id,
                QuestionPaper.subject_id == subject_id,
                QuestionPaper.year == year,
                QuestionPaper.set_code == set_code,
                QuestionPaper.data_origin == data_origin,
            )
            .first()
        )
        effective_set = f"{set_code}-{file_hash[:4]}" if existing_same_slot else set_code

        total_extracted_marks = int(round(sum(q.marks for q in extraction.questions))) or 80
        paper = QuestionPaper(
            exam_id=exam_id,
            subject_id=subject_id,
            source_id=source.id,
            title=f"{exam.name} {subject.name} {year} ({effective_set})",
            year=year,
            set_code=effective_set,
            paper_type=paper_type,
            language=language,
            total_marks=total_extracted_marks,
            document_hash=file_hash,
            storage_key=storage_key,
            source_url=source_url,
            is_verified=auto_verify,
            data_origin=data_origin,
            extraction_confidence=extraction.overall_confidence,
        )
        db.add(paper)
        db.flush()

        created_questions: list[Question] = []
        for eq in extraction.questions:
            q_obj = Question(
                question_paper_id=paper.id,
                question_number=eq.question_number,
                section_name=eq.section_name,
                page_number=eq.page_number,
                question_text=eq.question_text,
                normalized_text=eq.normalized_text,
                math_expressions_json=eq.math_expressions,
                question_type=eq.question_type,
                marks=eq.marks,
                difficulty="medium" if eq.marks <= 3 else "hard",
                is_competency_based=eq.question_type in ("case_study", "assertion_reason"),
                content_hash=eq.content_hash,
                language=language,
                verification_status="verified" if auto_verify else "pending",
                confidence_score=eq.confidence_score,
                data_origin=data_origin,
                source_reference=f"{paper.title} p.{eq.page_number} Q{eq.question_number}",
            )
            db.add(q_obj)
            db.flush()
            for opt in eq.options:
                db.add(
                    QuestionOption(
                        question_id=q_obj.id,
                        option_label=opt["option_label"],
                        option_text=opt["option_text"],
                        is_correct=opt["is_correct"],
                    )
                )
            if eq.answer_text:
                db.add(
                    QuestionAnswer(
                        question_id=q_obj.id,
                        answer_text=eq.answer_text,
                        is_official_key=True,
                    )
                )
            if not auto_verify:
                db.add(
                    ExtractionReview(
                        question_id=q_obj.id,
                        status="pending",
                        notes="Auto-queued from PDF ingestion",
                    )
                )
            created_questions.append(q_obj)

        db.commit()

        # Topic classification + embeddings + clustering
        for q_obj in created_questions:
            auto_classify_question_topic(db, q_obj, exam_id, subject_id)
        if created_questions:
            ensure_question_embeddings(db, created_questions)
            cluster_questions_for_subject(db, exam_id, subject_id)

        job.status = "spark_processing"
        job.pages_extracted = len(extraction.pages)
        job.questions_extracted = len(created_questions)
        job.question_paper_id = paper.id
        db.commit()

        run, summary = execute_medallion_from_db(db, trigger_type="pdf_upload")

        job.status = "completed" if run.status == "completed" else "failed"
        job.metrics_json = {
            "used_ocr_pages": extraction.used_ocr_pages,
            "warnings": extraction.warnings,
            "spark_run_id": str(run.id),
            "spark_duration_seconds": run.duration_seconds,
            "dq_passed": run.dq_passed,
            "gold_tables": summary.gold_tables if summary else {},
        }
        job.completed_at = datetime.now(timezone.utc)
        db.add(
            AuditLog(
                actor_user_id=current_user.id,
                action="document_uploaded_and_processed",
                resource_type="question_paper",
                resource_id=str(paper.id),
                details_json={"questions_extracted": len(created_questions), "file_hash": file_hash},
            )
        )
        db.commit()
        db.refresh(job)

        return {
            "job": IngestionJobOut.model_validate(job),
            "paper_id": str(paper.id),
            "questions_extracted": len(created_questions),
            "pages_extracted": len(extraction.pages),
            "spark_run_id": str(run.id),
            "spark_dq_passed": run.dq_passed,
        }
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc


@router.get("/ingestion/jobs", response_model=list[IngestionJobOut])
def list_ingestion_jobs(
    _admin: User = Depends(require_roles("admin", "teacher")),
    db: Session = Depends(get_db),
):
    jobs = db.query(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(50).all()
    return [IngestionJobOut.model_validate(j) for j in jobs]


@router.get("/processing-runs", response_model=list[ProcessingRunOut])
def list_processing_runs(
    _admin: User = Depends(require_roles("admin", "teacher")),
    db: Session = Depends(get_db),
):
    runs = db.query(ProcessingRun).order_by(ProcessingRun.started_at.desc()).limit(30).all()
    return [ProcessingRunOut.model_validate(r) for r in runs]


@router.post("/pipeline/run", response_model=ProcessingRunOut)
def trigger_medallion_pipeline(
    include_synthetic: bool = Query(default=False),
    _admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    run, _summary = execute_medallion_from_db(
        db=db,
        trigger_type="admin_manual",
        include_synthetic=include_synthetic,
    )
    return ProcessingRunOut.model_validate(run)


@router.get("/review-queue")
def get_review_queue(
    status_filter: str = Query(default="pending"),
    _admin: User = Depends(require_roles("admin", "teacher")),
    db: Session = Depends(get_db),
):
    questions = (
        db.query(Question)
        .filter(Question.verification_status == status_filter, Question.is_deleted.is_(False))
        .order_by(Question.created_at.desc())
        .limit(50)
        .all()
    )
    papers = {
        p.id: p
        for p in db.query(QuestionPaper)
        .filter(QuestionPaper.id.in_([q.question_paper_id for q in questions]))
        .all()
    } if questions else {}
    return {
        "count": len(questions),
        "items": [
            {
                "id": str(q.id),
                "question_number": q.question_number,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "marks": float(q.marks),
                "difficulty": q.difficulty,
                "confidence_score": float(q.confidence_score),
                "verification_status": q.verification_status,
                "paper_title": papers[q.question_paper_id].title if q.question_paper_id in papers else None,
                "year": papers[q.question_paper_id].year if q.question_paper_id in papers else None,
            }
            for q in questions
        ],
    }


@router.post("/questions/{question_id}/verify")
def verify_question(
    question_id: uuid.UUID,
    payload: QuestionVerifyRequest,
    current_user: User = Depends(require_roles("admin", "teacher")),
    db: Session = Depends(get_db),
):
    q = db.query(Question).filter(Question.id == question_id, Question.is_deleted.is_(False)).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found.")

    q.verification_status = payload.verification_status
    if payload.question_text:
        q.question_text = payload.question_text.strip()
        q.normalized_text = q.question_text.lower()
    if payload.question_type:
        q.question_type = payload.question_type
    if payload.marks is not None:
        q.marks = payload.marks
    if payload.difficulty:
        q.difficulty = payload.difficulty
    if payload.topic_id:
        db.query(QuestionTopic).filter(
            QuestionTopic.question_id == q.id, QuestionTopic.is_primary.is_(True)
        ).delete()
        db.add(
            QuestionTopic(
                question_id=q.id,
                topic_id=payload.topic_id,
                is_primary=True,
                confidence=1.0,
                assigned_by="human_reviewer",
            )
        )

    review = db.query(ExtractionReview).filter(ExtractionReview.question_id == q.id).first()
    if review:
        review.status = payload.verification_status
        review.reviewer_id = current_user.id
        review.notes = payload.notes
        review.reviewed_at = datetime.now(timezone.utc)
    else:
        db.add(
            ExtractionReview(
                question_id=q.id,
                reviewer_id=current_user.id,
                status=payload.verification_status,
                notes=payload.notes,
                reviewed_at=datetime.now(timezone.utc),
            )
        )

    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="question_verified",
            resource_type="question",
            resource_id=str(q.id),
            details_json={"status": payload.verification_status},
        )
    )
    db.commit()
    return {"status": "updated", "question_id": str(q.id), "verification_status": q.verification_status}


@router.get("/data-quality")
def get_data_quality_summary(
    _admin: User = Depends(require_roles("admin", "teacher")),
    db: Session = Depends(get_db),
):
    latest_run = (
        db.query(ProcessingRun)
        .order_by(ProcessingRun.started_at.desc())
        .first()
    )
    total_q = db.query(Question).filter(Question.is_deleted.is_(False)).count()
    verified_q = (
        db.query(Question)
        .filter(Question.is_deleted.is_(False), Question.verification_status == "verified")
        .count()
    )
    pending_q = (
        db.query(Question)
        .filter(Question.is_deleted.is_(False), Question.verification_status == "pending")
        .count()
    )
    unmapped_q = total_q - db.query(QuestionTopic.question_id).distinct().count()

    return {
        "total_questions": total_q,
        "verified_questions": verified_q,
        "pending_review_questions": pending_q,
        "unmapped_topic_questions": max(0, unmapped_q),
        "latest_spark_run": ProcessingRunOut.model_validate(latest_run) if latest_run else None,
    }
