from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models.core_exam import SyllabusTopic
from app.models.question_intel import Question, QuestionPaper, QuestionTopic

TREND_DISCLAIMER = (
    "Historical trends reflect past examination blueprints and papers only. "
    "They do not predict or guarantee future examination questions or mark distributions."
)


def compare_exam_years(
    db: Session,
    exam_id: uuid.UUID,
    subject_id: uuid.UUID,
    year_a: int,
    year_b: int,
) -> dict[str, Any]:
    papers = (
        db.query(QuestionPaper)
        .filter(
            QuestionPaper.exam_id == exam_id,
            QuestionPaper.subject_id == subject_id,
            QuestionPaper.is_deleted.is_(False),
            QuestionPaper.data_origin != "synthetic_dev",
        )
        .order_by(QuestionPaper.year.asc())
        .all()
    )
    if not papers:
        return {
            "exam_id": exam_id,
            "subject_id": subject_id,
            "year_a": year_a,
            "year_b": year_b,
            "has_data": False,
            "chapter_shifts": [],
            "question_type_shifts": [],
            "difficulty_shifts": [],
            "competency_shift_pct": 0.0,
            "yearly_series": [],
            "disclaimer": TREND_DISCLAIMER,
        }

    paper_map = {p.id: p for p in papers}
    questions = (
        db.query(Question)
        .filter(
            Question.question_paper_id.in_(list(paper_map.keys())),
            Question.is_deleted.is_(False),
        )
        .all()
    )
    q_topics = {
        qt.question_id: qt.topic_id
        for qt in db.query(QuestionTopic)
        .filter(QuestionTopic.question_id.in_([q.id for q in questions]), QuestionTopic.is_primary.is_(True))
        .all()
    } if questions else {}
    topics = {
        t.id: t
        for t in db.query(SyllabusTopic).filter(SyllabusTopic.id.in_(list(q_topics.values()))).all()
    } if q_topics else {}

    def _agg_for_year(yr: int):
        yr_qs = [q for q in questions if paper_map[q.question_paper_id].year == yr]
        total_m = sum(float(q.marks) for q in yr_qs) or 1.0
        total_q = len(yr_qs) or 1
        ch = defaultdict(float)
        qt = defaultdict(int)
        diff = defaultdict(int)
        comp = 0
        for q in yr_qs:
            t = topics.get(q_topics.get(q.id))
            ch_name = t.chapter_name if t else "Unmapped Chapter"
            ch[ch_name] += float(q.marks)
            qt[q.question_type] += 1
            diff[q.difficulty] += 1
            if q.is_competency_based:
                comp += 1
        return {
            "count": len(yr_qs),
            "total_marks": total_m,
            "chapters_pct": {k: round(100.0 * v / total_m, 2) for k, v in ch.items()},
            "qtypes_pct": {k: round(100.0 * v / total_q, 2) for k, v in qt.items()},
            "diffs_pct": {k: round(100.0 * v / total_q, 2) for k, v in diff.items()},
            "competency_pct": round(100.0 * comp / total_q, 2) if yr_qs else 0.0,
        }

    agg_a = _agg_for_year(year_a)
    agg_b = _agg_for_year(year_b)

    all_chapters = sorted(set(agg_a["chapters_pct"]) | set(agg_b["chapters_pct"]))
    chapter_shifts = [
        {
            "chapter_name": ch,
            "year_a_pct": agg_a["chapters_pct"].get(ch, 0.0),
            "year_b_pct": agg_b["chapters_pct"].get(ch, 0.0),
            "delta_pct": round(agg_b["chapters_pct"].get(ch, 0.0) - agg_a["chapters_pct"].get(ch, 0.0), 2),
        }
        for ch in all_chapters
    ]

    all_qtypes = sorted(set(agg_a["qtypes_pct"]) | set(agg_b["qtypes_pct"]))
    qtype_shifts = [
        {
            "question_type": qt,
            "year_a_pct": agg_a["qtypes_pct"].get(qt, 0.0),
            "year_b_pct": agg_b["qtypes_pct"].get(qt, 0.0),
            "delta_pct": round(agg_b["qtypes_pct"].get(qt, 0.0) - agg_a["qtypes_pct"].get(qt, 0.0), 2),
        }
        for qt in all_qtypes
    ]

    all_diffs = ["easy", "medium", "hard"]
    diff_shifts = [
        {
            "difficulty": d,
            "year_a_pct": agg_a["diffs_pct"].get(d, 0.0),
            "year_b_pct": agg_b["diffs_pct"].get(d, 0.0),
            "delta_pct": round(agg_b["diffs_pct"].get(d, 0.0) - agg_a["diffs_pct"].get(d, 0.0), 2),
        }
        for d in all_diffs
    ]

    # Full yearly series
    diff_num = {"easy": 1.0, "medium": 2.0, "hard": 3.0}
    yr_buckets = defaultdict(lambda: {"papers": set(), "q": 0, "m": 0.0, "comp": 0, "dsum": 0.0})
    for q in questions:
        p = paper_map[q.question_paper_id]
        b = yr_buckets[p.year]
        b["papers"].add(p.id)
        b["q"] += 1
        b["m"] += float(q.marks)
        b["comp"] += 1 if q.is_competency_based else 0
        b["dsum"] += diff_num.get(q.difficulty, 2.0)

    yearly_series = [
        {
            "year": yr,
            "papers_count": len(b["papers"]),
            "questions_count": b["q"],
            "total_marks": round(b["m"], 2),
            "competency_share_pct": round(100.0 * b["comp"] / max(b["q"], 1), 2),
            "avg_difficulty_score": round(b["dsum"] / max(b["q"], 1), 3),
        }
        for yr, b in sorted(yr_buckets.items())
    ]

    return {
        "exam_id": exam_id,
        "subject_id": subject_id,
        "year_a": year_a,
        "year_b": year_b,
        "has_data": agg_a["count"] > 0 or agg_b["count"] > 0,
        "chapter_shifts": sorted(chapter_shifts, key=lambda x: abs(x["delta_pct"]), reverse=True),
        "question_type_shifts": qtype_shifts,
        "difficulty_shifts": diff_shifts,
        "competency_shift_pct": round(agg_b["competency_pct"] - agg_a["competency_pct"], 2),
        "yearly_series": yearly_series,
        "disclaimer": TREND_DISCLAIMER,
    }
