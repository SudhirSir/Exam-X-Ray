from __future__ import annotations

import hashlib
import tempfile
import uuid
from pathlib import Path

from spark.medallion import load_gold_snapshot, run_medallion_pipeline


def test_pyspark_medallion_dedup_dq_and_idempotency():
    exam_id = str(uuid.uuid4())
    subj_id = str(uuid.uuid4())
    paper_id = str(uuid.uuid4())
    topic_id = str(uuid.uuid4())

    q_text = "Find the discriminant of x^2 - 5x + 6 = 0."
    q_hash = hashlib.sha256(q_text.lower().encode()).hexdigest()

    records = [
        {
            "question_id": str(uuid.uuid4()),
            "paper_id": paper_id,
            "exam_id": exam_id,
            "exam_code": "CBSE_10",
            "subject_id": subj_id,
            "subject_code": "MATH_10",
            "year": 2024,
            "set_code": "Set-1",
            "question_number": "1",
            "question_text": q_text,
            "question_type": "short_answer",
            "marks": 2.0,
            "difficulty": "medium",
            "is_competency_based": True,
            "topic_id": topic_id,
            "content_hash": q_hash,
            "verification_status": "verified",
            "confidence_score": 0.96,
            "data_origin": "verified_official",
        },
        # Exact duplicate in same paper & set -> should be deduplicated by Silver window
        {
            "question_id": str(uuid.uuid4()),
            "paper_id": paper_id,
            "exam_id": exam_id,
            "exam_code": "CBSE_10",
            "subject_id": subj_id,
            "subject_code": "MATH_10",
            "year": 2024,
            "set_code": "Set-1",
            "question_number": "1b",
            "question_text": q_text,
            "question_type": "short_answer",
            "marks": 2.0,
            "difficulty": "medium",
            "is_competency_based": True,
            "topic_id": topic_id,
            "content_hash": q_hash,
            "verification_status": "verified",
            "confidence_score": 0.80,
            "data_origin": "verified_official",
        },
        # Distinct valid question
        {
            "question_id": str(uuid.uuid4()),
            "paper_id": paper_id,
            "exam_id": exam_id,
            "exam_code": "CBSE_10",
            "subject_id": subj_id,
            "subject_code": "MATH_10",
            "year": 2023,
            "set_code": "Set-1",
            "question_number": "2",
            "question_text": "Evaluate sin^2(30 deg) + cos^2(30 deg).",
            "question_type": "mcq",
            "marks": 1.0,
            "difficulty": "easy",
            "is_competency_based": False,
            "topic_id": topic_id,
            "content_hash": hashlib.sha256(b"trig_q2").hexdigest(),
            "verification_status": "verified",
            "confidence_score": 0.99,
            "data_origin": "verified_official",
        },
    ]

    topics = [
        {
            "id": topic_id,
            "chapter_name": "Quadratic Equations",
            "topic_name": "Discriminant & Roots",
            "official_weightage_marks": 7.0,
            "importance_score": 0.9,
        }
    ]

    activities = [
        {
            "event_id": str(uuid.uuid4()),
            "analytics_pseudo_id": "stu_test001",
            "exam_id": exam_id,
            "subject_id": subj_id,
            "topic_id": topic_id,
            "chapter_name": "Quadratic Equations",
            "topic_name": "Discriminant & Roots",
            "is_correct": False,
            "time_spent_seconds": 140,
            "difficulty": "medium",
            "occurred_at": "2026-11-12T10:00:00Z",
        }
    ]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        run1 = run_medallion_pipeline(records, topics, activities, base_dir=tmp_path)
        assert run1.records_bronze == 3
        assert run1.records_silver == 2
        assert run1.duplicates_removed == 1
        assert run1.dq_passed is True
        assert set(run1.gold_tables.keys()) == {
            "exam_year_metrics",
            "chapter_weightage",
            "question_type_distribution",
            "question_clusters",
            "difficulty_distribution",
            "topic_trends",
            "pattern_changes",
            "student_topic_mastery",
            "revision_priorities",
        }

        # Idempotency check: second run yields identical Gold counts
        run2 = run_medallion_pipeline(records, topics, activities, base_dir=tmp_path)
        assert run2.records_silver == run1.records_silver
        assert run2.gold_tables == run1.gold_tables

        cw = load_gold_snapshot("chapter_weightage", base_dir=tmp_path)
        assert len(cw) == 1
        assert cw[0]["weightage_pct"] == 100.0
