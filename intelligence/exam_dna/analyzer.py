from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models.core_exam import Exam, Subject, SyllabusTopic
from app.models.question_intel import Question, QuestionPaper, QuestionTopic
from spark.medallion import load_gold_snapshot


DIFF_SCORE_MAP = {"easy": 1.0, "medium": 2.0, "hard": 3.0}

EXAM_DNA_DISCLAIMER = (
    "Exam DNA analytics are computed exclusively from verified historical examination "
    "papers and official blueprints stored in the registry. Historical distributions do "
    "not guarantee future examination weightage."
)


def build_exam_dna_report(
    db: Session,
    exam_id: uuid.UUID,
    subject_id: uuid.UUID,
    year_from: int | None = None,
    year_to: int | None = None,
    include_synthetic: bool = False,
) -> dict[str, Any]:
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not exam or not subject:
        raise ValueError("Exam or subject not found")

    paper_query = db.query(QuestionPaper).filter(
        QuestionPaper.exam_id == exam_id,
        QuestionPaper.subject_id == subject_id,
        QuestionPaper.is_deleted.is_(False),
    )
    if not include_synthetic:
        paper_query = paper_query.filter(QuestionPaper.data_origin != "synthetic_dev")
    if year_from is not None:
        paper_query = paper_query.filter(QuestionPaper.year >= year_from)
    if year_to is not None:
        paper_query = paper_query.filter(QuestionPaper.year <= year_to)

    papers = paper_query.order_by(QuestionPaper.year.asc()).all()
    if not papers:
        return {
            "exam_id": exam.id,
            "exam_name": exam.name,
            "subject_id": subject.id,
            "subject_name": subject.name,
            "year_from": year_from,
            "year_to": year_to,
            "has_data": False,
            "total_analyzed_papers": 0,
            "total_verified_questions": 0,
            "total_questions_all_origins": 0,
            "data_confidence_score": 0.0,
            "computation_source": "empty",
            "chapter_weightage": [],
            "question_type_distribution": [],
            "difficulty_distribution": [],
            "yearly_trends": [],
            "recurring_concepts": [],
            "sources": [],
            "disclaimer": EXAM_DNA_DISCLAIMER,
        }

    paper_ids = [p.id for p in papers]
    paper_map = {p.id: p for p in papers}

    questions = (
        db.query(Question)
        .filter(
            Question.question_paper_id.in_(paper_ids),
            Question.is_deleted.is_(False),
        )
        .all()
    )

    verified_questions = [q for q in questions if q.verification_status == "verified"]
    active_questions = verified_questions if verified_questions else questions

    # Topic lookups
    topic_links = (
        db.query(QuestionTopic)
        .filter(QuestionTopic.question_id.in_([q.id for q in active_questions]), QuestionTopic.is_primary.is_(True))
        .all()
    ) if active_questions else []
    q_to_topic_id = {tl.question_id: tl.topic_id for tl in topic_links}
    topics = {
        t.id: t
        for t in db.query(SyllabusTopic).filter(SyllabusTopic.id.in_(list(q_to_topic_id.values()))).all()
    } if q_to_topic_id else {}

    # Check if Gold PySpark snapshots cover this exam+subject and unfiltered period
    gold_chapters = [
        r for r in load_gold_snapshot("chapter_weightage")
        if r.get("exam_id") == str(exam_id) and r.get("subject_id") == str(subject_id)
    ]
    use_gold = bool(gold_chapters) and year_from is None and year_to is None

    if use_gold:
        chapter_weightage = [
            {
                "chapter_name": r["chapter_name"],
                "total_marks": float(r["total_marks"]),
                "question_count": int(r["question_count"]),
                "weightage_pct": float(r["weightage_pct"]),
                "avg_difficulty_score": float(r["avg_difficulty_score"]),
            }
            for r in sorted(gold_chapters, key=lambda x: float(x["total_marks"]), reverse=True)
        ]
        gold_qtypes = [
            r for r in load_gold_snapshot("question_type_distribution")
            if r.get("exam_id") == str(exam_id) and r.get("subject_id") == str(subject_id)
        ]
        question_type_distribution = [
            {
                "question_type": r["question_type"],
                "question_count": int(r["question_count"]),
                "total_marks": float(r["total_marks"]),
                "share_pct": float(r["share_pct"]),
            }
            for r in sorted(gold_qtypes, key=lambda x: int(x["question_count"]), reverse=True)
        ]
        gold_diff = [
            r for r in load_gold_snapshot("difficulty_distribution")
            if r.get("exam_id") == str(exam_id) and r.get("subject_id") == str(subject_id)
        ]
        difficulty_distribution = [
            {
                "difficulty": r["difficulty"],
                "question_count": int(r["question_count"]),
                "total_marks": float(r["total_marks"]),
                "share_pct": float(r["share_pct"]),
            }
            for r in gold_diff
        ]
        gold_yearly = [
            r for r in load_gold_snapshot("exam_year_metrics")
            if r.get("exam_id") == str(exam_id) and r.get("subject_id") == str(subject_id)
        ]
        yearly_trends = [
            {
                "year": int(r["year"]),
                "papers_count": int(r["papers_count"]),
                "questions_count": int(r["questions_count"]),
                "total_marks": float(r["total_marks"]),
                "competency_share_pct": float(r["competency_share_pct"]),
                "avg_difficulty_score": float(r["avg_difficulty_score"]),
            }
            for r in sorted(gold_yearly, key=lambda x: int(x["year"]))
        ]
        computation_source = "gold_spark_delta"
    else:
        computation_source = "live_sql_fallback"
        ch_agg: dict[str, dict[str, Any]] = defaultdict(lambda: {"marks": 0.0, "count": 0, "diff_sum": 0.0})
        qt_agg: dict[str, dict[str, Any]] = defaultdict(lambda: {"marks": 0.0, "count": 0})
        diff_agg: dict[str, dict[str, Any]] = defaultdict(lambda: {"marks": 0.0, "count": 0})
        yr_agg: dict[int, dict[str, Any]] = defaultdict(
            lambda: {"papers": set(), "count": 0, "marks": 0.0, "comp": 0, "diff_sum": 0.0}
        )

        total_marks_all = 0.0
        for q in active_questions:
            p = paper_map[q.question_paper_id]
            t = topics.get(q_to_topic_id.get(q.id))
            ch_name = t.chapter_name if t else "Unmapped Chapter"
            d_score = DIFF_SCORE_MAP.get(q.difficulty, 2.0)

            ch_agg[ch_name]["marks"] += float(q.marks)
            ch_agg[ch_name]["count"] += 1
            ch_agg[ch_name]["diff_sum"] += d_score
            total_marks_all += float(q.marks)

            qt_agg[q.question_type]["marks"] += float(q.marks)
            qt_agg[q.question_type]["count"] += 1

            diff_agg[q.difficulty]["marks"] += float(q.marks)
            diff_agg[q.difficulty]["count"] += 1

            yr_agg[p.year]["papers"].add(p.id)
            yr_agg[p.year]["count"] += 1
            yr_agg[p.year]["marks"] += float(q.marks)
            yr_agg[p.year]["comp"] += 1 if q.is_competency_based else 0
            yr_agg[p.year]["diff_sum"] += d_score

        total_q = max(len(active_questions), 1)
        denom_marks = max(total_marks_all, 1.0)
        chapter_weightage = [
            {
                "chapter_name": ch,
                "total_marks": round(v["marks"], 2),
                "question_count": v["count"],
                "weightage_pct": round(100.0 * v["marks"] / denom_marks, 2),
                "avg_difficulty_score": round(v["diff_sum"] / max(v["count"], 1), 3),
            }
            for ch, v in sorted(ch_agg.items(), key=lambda kv: kv[1]["marks"], reverse=True)
        ]
        question_type_distribution = [
            {
                "question_type": qt,
                "question_count": v["count"],
                "total_marks": round(v["marks"], 2),
                "share_pct": round(100.0 * v["count"] / total_q, 2),
            }
            for qt, v in sorted(qt_agg.items(), key=lambda kv: kv[1]["count"], reverse=True)
        ]
        difficulty_distribution = [
            {
                "difficulty": d,
                "question_count": v["count"],
                "total_marks": round(v["marks"], 2),
                "share_pct": round(100.0 * v["count"] / total_q, 2),
            }
            for d, v in diff_agg.items()
        ]
        yearly_trends = [
            {
                "year": yr,
                "papers_count": len(v["papers"]),
                "questions_count": v["count"],
                "total_marks": round(v["marks"], 2),
                "competency_share_pct": round(100.0 * v["comp"] / max(v["count"], 1), 2),
                "avg_difficulty_score": round(v["diff_sum"] / max(v["count"], 1), 3),
            }
            for yr, v in sorted(yr_agg.items(), key=lambda kv: kv[0])
        ]

    # Recurring concepts with source references
    concept_agg: dict[str, dict[str, Any]] = {}
    for q in active_questions:
        p = paper_map[q.question_paper_id]
        t = topics.get(q_to_topic_id.get(q.id))
        if not t:
            continue
        key = str(t.id)
        if key not in concept_agg:
            concept_agg[key] = {
                "topic_id": key,
                "chapter_name": t.chapter_name,
                "topic_name": t.topic_name,
                "years": set(),
                "count": 0,
                "marks": 0.0,
                "refs": set(),
            }
        concept_agg[key]["years"].add(p.year)
        concept_agg[key]["count"] += 1
        concept_agg[key]["marks"] += float(q.marks)
        concept_agg[key]["refs"].add(f"{p.title} (Q{q.question_number})")

    recurring_concepts = [
        {
            "topic_id": v["topic_id"],
            "chapter_name": v["chapter_name"],
            "topic_name": v["topic_name"],
            "years_appeared": sorted(v["years"]),
            "occurrence_count": v["count"],
            "total_marks_across_years": round(v["marks"], 2),
            "source_references": sorted(v["refs"])[:6],
        }
        for v in sorted(
            concept_agg.values(),
            key=lambda x: (len(x["years"]), x["count"], x["marks"]),
            reverse=True,
        )[:15]
    ]

    paper_q_counts: dict[uuid.UUID, int] = defaultdict(int)
    for q in questions:
        paper_q_counts[q.question_paper_id] += 1

    sources = [
        {
            "paper_id": str(p.id),
            "title": p.title,
            "year": p.year,
            "set_code": p.set_code,
            "data_origin": p.data_origin,
            "is_verified": p.is_verified,
            "extraction_confidence": float(p.extraction_confidence),
            "source_url": p.source_url,
            "question_count": paper_q_counts[p.id],
        }
        for p in papers
    ]

    avg_conf = (
        sum(float(q.confidence_score) for q in active_questions) / len(active_questions)
        if active_questions
        else 0.0
    )
    verified_ratio = (len(verified_questions) / len(questions)) if questions else 0.0
    data_confidence = round(0.6 * avg_conf + 0.4 * verified_ratio, 3)

    return {
        "exam_id": exam.id,
        "exam_name": exam.name,
        "subject_id": subject.id,
        "subject_name": subject.name,
        "year_from": year_from or min(p.year for p in papers),
        "year_to": year_to or max(p.year for p in papers),
        "has_data": True,
        "total_analyzed_papers": len(papers),
        "total_verified_questions": len(verified_questions),
        "total_questions_all_origins": len(questions),
        "data_confidence_score": data_confidence,
        "computation_source": computation_source,
        "chapter_weightage": chapter_weightage,
        "question_type_distribution": question_type_distribution,
        "difficulty_distribution": difficulty_distribution,
        "yearly_trends": yearly_trends,
        "recurring_concepts": recurring_concepts,
        "sources": sources,
        "disclaimer": EXAM_DNA_DISCLAIMER,
    }
