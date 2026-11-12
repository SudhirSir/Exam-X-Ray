from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import uuid

_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(_ROOT), str(_ROOT / "apps" / "api")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.core_exam import Exam, Subject
from app.models.question_intel import DataSource, Question, QuestionPaper


def seed_synthetic_load_test_data(db: Session, count: int = 200) -> dict:
    """
    Creates clearly tagged synthetic development/load-test records (`data_origin='synthetic_dev'`).
    Excluded by default from verified Exam DNA analytics.
    """
    cbse10 = db.query(Exam).filter(Exam.code == "CBSE_10").first()
    math = db.query(Subject).filter(Subject.code == "MATH_10").first()
    if not cbse10 or not math:
        raise RuntimeError("Run seed_verified_cbse_data first.")

    src = DataSource(
        name="Synthetic Load-Test Fixture Generator",
        source_type="synthetic_dev",
        license_status="synthetic_internal",
        is_verified=False,
        data_origin="synthetic_dev",
        notes="Non-production synthetic records for load & Spark throughput testing only.",
    )
    db.add(src)
    db.flush()

    paper_hash = hashlib.sha256(f"synth:{uuid.uuid4()}".encode()).hexdigest()
    paper = QuestionPaper(
        exam_id=cbse10.id,
        subject_id=math.id,
        source_id=src.id,
        title="SYNTHETIC LOAD TEST FIXTURE PAPER",
        year=2024,
        set_code=f"SYNTH-{paper_hash[:6]}",
        paper_type="synthetic_fixture",
        document_hash=paper_hash,
        is_verified=False,
        data_origin="synthetic_dev",
        extraction_confidence=1.0,
    )
    db.add(paper)
    db.flush()

    q_types = ["mcq", "very_short", "short_answer", "long_answer"]
    diffs = ["easy", "medium", "hard"]
    for i in range(count):
        txt = f"[SYNTHETIC FIXTURE #{i}] Evaluate algebraic expression x^2 + {i}x + {(i*2)%19} = 0."
        db.add(
            Question(
                question_paper_id=paper.id,
                question_number=str(i + 1),
                question_text=txt,
                normalized_text=txt.lower(),
                question_type=q_types[i % len(q_types)],
                marks=float((i % 5) + 1),
                difficulty=diffs[i % len(diffs)],
                content_hash=hashlib.sha256(txt.encode()).hexdigest(),
                verification_status="pending",
                confidence_score=1.0,
                data_origin="synthetic_dev",
                source_reference="Synthetic Dev Fixture",
            )
        )
    db.commit()
    return {"status": "seeded_synthetic", "count": count, "paper_id": str(paper.id)}


if __name__ == "__main__":
    db = SessionLocal()
    try:
        print(seed_synthetic_load_test_data(db, count=100))
    finally:
        db.close()
