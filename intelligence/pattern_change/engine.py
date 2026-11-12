from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.core_exam import ExamBlueprint, ExamSubject, ExamVersion, SyllabusTopic, SyllabusVersion


def detect_pattern_changes(
    db: Session,
    exam_id: uuid.UUID,
    subject_id: uuid.UUID,
) -> dict[str, Any]:
    versions = (
        db.query(ExamVersion)
        .filter(ExamVersion.exam_id == exam_id)
        .order_by(ExamVersion.academic_year.asc())
        .all()
    )
    es = (
        db.query(ExamSubject)
        .filter(ExamSubject.exam_id == exam_id, ExamSubject.subject_id == subject_id)
        .first()
    )

    changes: list[dict[str, Any]] = []
    prev_summary = None
    curr_summary = None

    if len(versions) >= 2 and es:
        prev_v = versions[-2]
        curr_v = versions[-1]
        prev_bps = (
            db.query(ExamBlueprint)
            .filter(ExamBlueprint.exam_version_id == prev_v.id, ExamBlueprint.exam_subject_id == es.id)
            .all()
        )
        curr_bps = (
            db.query(ExamBlueprint)
            .filter(ExamBlueprint.exam_version_id == curr_v.id, ExamBlueprint.exam_subject_id == es.id)
            .all()
        )

        def _summarize_version(v: ExamVersion, bps: list[ExamBlueprint]) -> dict[str, Any]:
            total_q = sum(b.question_count for b in bps)
            comp_marks = sum(b.total_section_marks for b in bps if b.is_competency_based)
            total_sec_marks = sum(b.total_section_marks for b in bps) or v.total_marks
            return {
                "academic_year": v.academic_year,
                "version_code": v.version_code,
                "total_marks": v.total_marks,
                "duration_minutes": v.duration_minutes,
                "total_questions": total_q,
                "competency_marks": comp_marks,
                "competency_share_pct": round(100.0 * comp_marks / max(total_sec_marks, 1), 1),
                "sections": [
                    {
                        "section_name": b.section_name,
                        "question_type": b.question_type,
                        "question_count": b.question_count,
                        "marks_per_question": b.marks_per_question,
                        "total_section_marks": b.total_section_marks,
                        "is_competency_based": b.is_competency_based,
                    }
                    for b in bps
                ],
            }

        prev_summary = _summarize_version(prev_v, prev_bps)
        curr_summary = _summarize_version(curr_v, curr_bps)

        if prev_v.total_marks != curr_v.total_marks:
            changes.append(
                {
                    "from_year": prev_v.academic_year,
                    "to_year": curr_v.academic_year,
                    "change_category": "total_marks",
                    "summary": f"Total theory marks changed from {prev_v.total_marks} to {curr_v.total_marks}.",
                    "previous_value": prev_v.total_marks,
                    "current_value": curr_v.total_marks,
                    "impact_on_preparation": "Adjust time-per-mark pacing during full-length mock practice.",
                    "supporting_sources": [prev_v.version_code, curr_v.version_code],
                }
            )

        comp_delta = round(curr_summary["competency_share_pct"] - prev_summary["competency_share_pct"], 1)
        if abs(comp_delta) >= 1.0:
            changes.append(
                {
                    "from_year": prev_v.academic_year,
                    "to_year": curr_v.academic_year,
                    "change_category": "competency_distribution",
                    "summary": (
                        f"Competency-based & case-study share shifted from "
                        f"{prev_summary['competency_share_pct']}% to {curr_summary['competency_share_pct']}%."
                    ),
                    "previous_value": f"{prev_summary['competency_share_pct']}%",
                    "current_value": f"{curr_summary['competency_share_pct']}%",
                    "impact_on_preparation": (
                        "Prioritize application, assertion-reason, and real-world case study problems "
                        "over pure rote memorization."
                    ),
                    "supporting_sources": [prev_v.version_code, curr_v.version_code],
                }
            )

        prev_secs = {b.section_name: b for b in prev_bps}
        curr_secs = {b.section_name: b for b in curr_bps}
        for sec in sorted(set(prev_secs) | set(curr_secs)):
            pb = prev_secs.get(sec)
            cb = curr_secs.get(sec)
            if not pb and cb:
                changes.append(
                    {
                        "from_year": prev_v.academic_year,
                        "to_year": curr_v.academic_year,
                        "change_category": "section_added",
                        "summary": f"Added {sec} ({cb.question_count} x {cb.marks_per_question} marks, {cb.question_type}).",
                        "previous_value": None,
                        "current_value": f"{cb.question_count} questions ({cb.total_section_marks} marks)",
                        "impact_on_preparation": f"Practice {cb.question_type} format specifically for {sec}.",
                        "supporting_sources": [curr_v.version_code],
                    }
                )
            elif pb and cb and (
                pb.question_count != cb.question_count
                or pb.total_section_marks != cb.total_section_marks
                or pb.question_type != cb.question_type
            ):
                changes.append(
                    {
                        "from_year": prev_v.academic_year,
                        "to_year": curr_v.academic_year,
                        "change_category": "section_format_change",
                        "summary": (
                            f"{sec} updated from {pb.question_count} {pb.question_type} ({pb.total_section_marks}m) "
                            f"to {cb.question_count} {cb.question_type} ({cb.total_section_marks}m)."
                        ),
                        "previous_value": f"{pb.question_count} x {pb.marks_per_question}m ({pb.question_type})",
                        "current_value": f"{cb.question_count} x {cb.marks_per_question}m ({cb.question_type})",
                        "impact_on_preparation": f"Rebalance section timing and format drills for {sec}.",
                        "supporting_sources": [prev_v.version_code, curr_v.version_code],
                    }
                )

    # Check syllabus version topic additions/removals
    if es:
        svs = (
            db.query(SyllabusVersion)
            .filter(SyllabusVersion.exam_subject_id == es.id)
            .order_by(SyllabusVersion.academic_year.asc())
            .all()
        )
        if len(svs) >= 2:
            sv_prev, sv_curr = svs[-2], svs[-1]
            prev_topics = {
                t.topic_code: t.topic_name
                for t in db.query(SyllabusTopic).filter(SyllabusTopic.syllabus_version_id == sv_prev.id).all()
            }
            curr_topics = {
                t.topic_code: t.topic_name
                for t in db.query(SyllabusTopic).filter(SyllabusTopic.syllabus_version_id == sv_curr.id).all()
            }
            removed = sorted(set(prev_topics) - set(curr_topics))
            added = sorted(set(curr_topics) - set(prev_topics))
            if removed:
                changes.append(
                    {
                        "from_year": sv_prev.academic_year,
                        "to_year": sv_curr.academic_year,
                        "change_category": "syllabus_topics_removed",
                        "summary": f"{len(removed)} topic(s) rationalised/removed: {', '.join(prev_topics[c] for c in removed[:4])}.",
                        "previous_value": [prev_topics[c] for c in removed],
                        "current_value": [],
                        "impact_on_preparation": "Avoid spending revision hours on rationalised topics excluded from the current syllabus.",
                        "supporting_sources": [sv_prev.version_tag, sv_curr.version_tag],
                    }
                )
            if added:
                changes.append(
                    {
                        "from_year": sv_prev.academic_year,
                        "to_year": sv_curr.academic_year,
                        "change_category": "syllabus_topics_added",
                        "summary": f"{len(added)} topic(s) added: {', '.join(curr_topics[c] for c in added[:4])}.",
                        "previous_value": [],
                        "current_value": [curr_topics[c] for c in added],
                        "impact_on_preparation": "Ensure newly added syllabus topics are covered via textbook examples and sample papers.",
                        "supporting_sources": [sv_curr.version_tag],
                    }
                )

    return {
        "exam_id": exam_id,
        "subject_id": subject_id,
        "previous_version": prev_summary,
        "current_version": curr_summary,
        "changes": changes,
        "disclaimer": (
            "Pattern change diffs are derived directly from registered official blueprints and syllabus versions. "
            "Always confirm final notifications with the official examination board."
        ),
    }
