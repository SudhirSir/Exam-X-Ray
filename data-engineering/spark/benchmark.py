from __future__ import annotations

import hashlib
from pathlib import Path
import random
import shutil
import sys
import time
import uuid
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "apps" / "api"), str(_ROOT / "data-engineering")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pandas as pd

from spark.medallion import run_medallion_pipeline


def generate_synthetic_questions(n: int = 5000) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(42)
    exam_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "bench-exam"))
    subject_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "bench-math"))
    chapters = [
        ("Real Numbers", "Euclid Division & Fundamental Theorem"),
        ("Polynomials", "Zeroes of Quadratic Polynomials"),
        ("Quadratic Equations", "Discriminant and Nature of Roots"),
        ("Triangles", "Basic Proportionality Theorem"),
        ("Trigonometry", "Trigonometric Identities"),
        ("Surface Areas and Volumes", "Combinations of Solids"),
        ("Statistics", "Mean Median Mode Grouped Data"),
        ("Probability", "Classical Probability"),
    ]
    topics = [
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"topic-{i}")),
            "chapter_name": ch,
            "topic_name": tp,
            "official_weightage_marks": 6.0,
            "importance_score": 0.8,
        }
        for i, (ch, tp) in enumerate(chapters)
    ]

    q_types = ["mcq", "very_short", "short_answer", "long_answer", "case_study"]
    diffs = ["easy", "medium", "hard"]
    records: list[dict[str, Any]] = []
    for i in range(n):
        ch_idx = i % len(topics)
        t = topics[ch_idx]
        year = 2019 + (i % 7)
        q_text = f"Synthetic load-test problem #{i}: Solve {t['topic_name']} variant {i % 900}."
        records.append(
            {
                "question_id": str(uuid.uuid4()),
                "paper_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"paper-{year}")),
                "exam_id": exam_id,
                "exam_code": "SYNTH_BENCH",
                "subject_id": subject_id,
                "subject_code": "MATH_BENCH",
                "year": year,
                "set_code": f"Set-{(i % 3) + 1}",
                "question_number": str((i % 38) + 1),
                "section_name": "Section A",
                "question_text": q_text,
                "question_type": q_types[i % len(q_types)],
                "marks": float([1, 1, 2, 3, 5][i % 5]),
                "difficulty": diffs[i % len(diffs)],
                "is_competency_based": (i % 4 == 0),
                "chapter_name": t["chapter_name"],
                "topic_id": t["id"],
                "topic_name": t["topic_name"],
                "content_hash": hashlib.sha256(q_text.encode()).hexdigest(),
                "verification_status": "verified",
                "confidence_score": 0.95,
                "data_origin": "synthetic_dev",
                "source_reference": f"Synthetic Benchmark {year}",
            }
        )
    return records, topics


def run_pandas_baseline(records: list[dict[str, Any]]) -> dict[str, Any]:
    t0 = time.perf_counter()
    df = pd.DataFrame(records)
    df["normalized_text"] = df["question_text"].str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
    df = df.drop_duplicates(subset=["exam_id", "subject_id", "year", "set_code", "content_hash"])
    _ = df.groupby(["exam_id", "subject_id", "year"]).agg(
        papers=("paper_id", "nunique"),
        questions=("question_id", "count"),
        total_marks=("marks", "sum"),
    )
    _ = df.groupby(["exam_id", "subject_id", "chapter_name"]).agg(
        questions=("question_id", "count"),
        total_marks=("marks", "sum"),
    )
    _ = df.groupby(["exam_id", "subject_id", "question_type"]).agg(
        questions=("question_id", "count"),
    )
    elapsed = round(time.perf_counter() - t0, 3)
    return {"pandas_seconds": elapsed, "rows_processed": len(df)}


def run_benchmark(n_rows: int = 5000) -> dict[str, Any]:
    records, topics = generate_synthetic_questions(n_rows)
    pandas_res = run_pandas_baseline(records)
    tmp_dir = _ROOT / "data" / "benchmark_tmp"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    try:
        spark_summary = run_medallion_pipeline(records, topics, base_dir=tmp_dir)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return {
        "dataset_rows": n_rows,
        "pandas_baseline": pandas_res,
        "pyspark_medallion": {
            "duration_seconds": spark_summary.duration_seconds,
            "delta_enabled": spark_summary.delta_enabled,
            "records_bronze": spark_summary.records_bronze,
            "records_silver": spark_summary.records_silver,
            "duplicates_removed": spark_summary.duplicates_removed,
            "dq_passed": spark_summary.dq_passed,
            "gold_tables": spark_summary.gold_tables,
        },
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_benchmark(5000), indent=2))
