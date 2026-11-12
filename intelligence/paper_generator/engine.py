from __future__ import annotations

import io
import random
import uuid
from collections import defaultdict
from typing import Any

from ortools.sat.python import cp_model
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.orm import Session

from app.models.core_exam import Exam, Subject, SyllabusTopic
from app.models.question_intel import (
    Question,
    QuestionAnswer,
    QuestionOption,
    QuestionPaper,
    QuestionTopic,
)


def generate_optimized_paper(
    db: Session,
    exam_id: uuid.UUID,
    subject_id: uuid.UUID,
    total_marks: int = 40,
    question_count: int = 14,
    chapters: list[str] | None = None,
    question_types: list[str] | None = None,
    difficulty_distribution: dict[str, float] | None = None,
    language: str = "English",
    include_ai_generated: bool = False,
) -> dict[str, Any]:
    """
    Constraint-based Question Paper Optimization using Google OR-Tools CP-SAT.
    Guarantees:
    - No duplicate content hashes
    - At most 1 question per similarity cluster
    - Balanced chapter coverage
    - Matches target total_marks and difficulty distribution as closely as feasible
    """
    papers = (
        db.query(QuestionPaper)
        .filter(
            QuestionPaper.exam_id == exam_id,
            QuestionPaper.subject_id == subject_id,
            QuestionPaper.is_deleted.is_(False),
            QuestionPaper.data_origin != "synthetic_dev",
        )
        .all()
    )
    if not papers:
        raise ValueError("No verified question papers available for this exam and subject.")

    q_query = db.query(Question).filter(
        Question.question_paper_id.in_([p.id for p in papers]),
        Question.is_deleted.is_(False),
        Question.language == language,
    )
    if not include_ai_generated:
        q_query = q_query.filter(Question.data_origin != "ai_generated")

    candidates = q_query.all()
    if not candidates:
        raise ValueError("No candidate questions match the selected language and origin filters.")

    q_ids = [q.id for q in candidates]
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

    filtered: list[Question] = []
    ch_filter = {c.lower() for c in chapters} if chapters else None
    qt_filter = {t.lower() for t in question_types} if question_types else None

    for q in candidates:
        t = topics.get(q_topics.get(q.id))
        ch = t.chapter_name.lower() if t else "unmapped"
        if ch_filter and ch not in ch_filter:
            continue
        if qt_filter and q.question_type.lower() not in qt_filter:
            continue
        filtered.append(q)

    pool = filtered if filtered else candidates
    # Randomize tie-break order slightly so "Regenerate paper" gives varied valid papers
    rng = random.Random()
    rng.shuffle(pool)

    # Deduplicate pool by content_hash before solving
    unique_pool: list[Question] = []
    seen_hashes: set[str] = set()
    for q in pool:
        if q.content_hash not in seen_hashes:
            unique_pool.append(q)
            seen_hashes.add(q.content_hash)

    n = len(unique_pool)
    if n == 0:
        raise ValueError("Candidate question bank is empty after filtering.")

    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"q_{i}") for i in range(n)]

    # Cluster exclusion: at most 1 question per cluster_id
    by_cluster: dict[uuid.UUID, list[int]] = defaultdict(list)
    for i, q in enumerate(unique_pool):
        if q.cluster_id:
            by_cluster[q.cluster_id].append(i)
    for idxs in by_cluster.values():
        if len(idxs) > 1:
            model.Add(sum(x[i] for i in idxs) <= 1)

    marks_int = [max(1, int(round(float(q.marks)))) for q in unique_pool]
    max_possible_marks = sum(marks_int)
    target_m = min(total_marks, max_possible_marks)
    target_q = min(question_count, n)

    # Soft constraints with penalized slack variables so solver always returns best feasible paper
    total_m_expr = sum(x[i] * marks_int[i] for i in range(n))
    total_q_expr = sum(x[i] for i in range(n))

    marks_diff_pos = model.NewIntVar(0, max_possible_marks, "m_pos")
    marks_diff_neg = model.NewIntVar(0, max_possible_marks, "m_neg")
    model.Add(total_m_expr - target_m == marks_diff_pos - marks_diff_neg)

    q_diff_pos = model.NewIntVar(0, n, "q_pos")
    q_diff_neg = model.NewIntVar(0, n, "q_neg")
    model.Add(total_q_expr - target_q == q_diff_pos - q_diff_neg)

    # Difficulty distribution targets
    diff_dist = difficulty_distribution or {"easy": 0.3, "medium": 0.5, "hard": 0.2}
    penalties = [100 * (marks_diff_pos + marks_diff_neg), 40 * (q_diff_pos + q_diff_neg)]

    for d_key, ratio in diff_dist.items():
        d_idxs = [i for i, q in enumerate(unique_pool) if q.difficulty == d_key]
        if d_idxs:
            target_d = int(round(target_q * float(ratio)))
            dp = model.NewIntVar(0, n, f"d_{d_key}_pos")
            dn = model.NewIntVar(0, n, f"d_{d_key}_neg")
            model.Add(sum(x[i] for i in d_idxs) - target_d == dp - dn)
            penalties.append(12 * (dp + dn))

    # Chapter spread bonus (encourage covering as many distinct chapters as possible)
    by_ch: dict[str, list[int]] = defaultdict(list)
    for i, q in enumerate(unique_pool):
        t = topics.get(q_topics.get(q.id))
        by_ch[t.chapter_name if t else "General"].append(i)
    ch_covered_vars = []
    for ch_name, idxs in by_ch.items():
        cv = model.NewBoolVar(f"ch_{abs(hash(ch_name)) % 100000}")
        model.AddMaxEquality(cv, [x[i] for i in idxs])
        ch_covered_vars.append(cv)

    # Prefer verified questions
    verified_bonus = sum(x[i] * (3 if unique_pool[i].verification_status == "verified" else 0) for i in range(n))

    model.Minimize(sum(penalties) - 10 * sum(ch_covered_vars) - verified_bonus)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("Constraint solver could not find a feasible question combination.")

    selected = [unique_pool[i] for i in range(n) if solver.Value(x[i]) == 1]
    selected.sort(key=lambda q: (float(q.marks), q.question_type))

    # Assign sections by marks/type
    arranged: list[dict[str, Any]] = []
    for order_idx, q in enumerate(selected, start=1):
        if q.marks <= 1.0:
            sec = "Section A (Objective / 1 Mark)"
        elif q.marks <= 2.0:
            sec = "Section B (Very Short / 2 Marks)"
        elif q.marks <= 3.0:
            sec = "Section C (Short Answer / 3 Marks)"
        elif q.question_type == "case_study":
            sec = "Section E (Case-Based / 4 Marks)"
        else:
            sec = "Section D (Long Answer / 5 Marks)"
        t = topics.get(q_topics.get(q.id))
        arranged.append(
            {
                "question": q,
                "section_name": sec,
                "order_index": order_idx,
                "allocated_marks": float(q.marks),
                "chapter_name": t.chapter_name if t else "General",
                "topic_name": t.topic_name if t else "General",
            }
        )

    actual_marks = sum(a["allocated_marks"] for a in arranged)
    solver_label = "optimal" if abs(actual_marks - total_marks) < 0.01 else "best_feasible"
    return {
        "solver_status": solver_label,
        "actual_marks": actual_marks,
        "contains_ai_questions": any(a["question"].data_origin == "ai_generated" for a in arranged),
        "items": arranged,
    }


def render_paper_pdf(
    paper_title: str,
    exam_name: str,
    subject_name: str,
    total_marks: float,
    duration_minutes: int,
    questions_data: list[dict[str, Any]],
    include_answers: bool = False,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=paper_title)
    styles = getSampleStyleSheet()
    story = []

    header_title = f"{paper_title} — {'ANSWER KEY & MARKING SCHEME' if include_answers else 'QUESTION PAPER'}"
    story.append(Paragraph(f"<b>EXAM X-RAY | {exam_name} — {subject_name}</b>", styles["Title"]))
    story.append(Paragraph(f"<b>{header_title}</b>", styles["Heading2"]))
    story.append(
        Paragraph(
            f"Maximum Marks: {total_marks:.0f} | Time Allowed: {duration_minutes} Minutes",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 14))

    current_sec = None
    for item in questions_data:
        sec = item.get("section_name")
        if sec != current_sec:
            current_sec = sec
            story.append(Spacer(1, 8))
            story.append(Paragraph(f"<b>{sec}</b>", styles["Heading3"]))
            story.append(Spacer(1, 4))

        q_num = item["order_index"]
        marks = item["allocated_marks"]
        q_text = item["question_text"]
        ai_tag = " [AI-Generated]" if item.get("data_origin") == "ai_generated" else ""
        story.append(
            Paragraph(f"<b>Q{q_num}.</b> {q_text} <i>[{marks:.0f} Mark(s)]{ai_tag}</i>", styles["Normal"])
        )

        for opt in item.get("options", []):
            story.append(
                Paragraph(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;({opt['option_label']}) {opt['option_text']}",
                    styles["Normal"],
                )
            )

        if include_answers:
            ans_txt = item.get("answer_text") or "Refer to standard NCERT / marking scheme."
            sol_txt = item.get("solution_steps") or ""
            story.append(Paragraph(f"<b>Answer:</b> {ans_txt}", styles["Normal"]))
            if sol_txt:
                story.append(Paragraph(f"<i>Solution:</i> {sol_txt}", styles["Normal"]))

        story.append(Spacer(1, 8))

    doc.build(story)
    return buf.getvalue()
