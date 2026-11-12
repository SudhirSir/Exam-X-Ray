from __future__ import annotations

from app.models.core_exam import Exam, Subject
from intelligence.question_similarity.engine import classify_relationship, cosine_similarity, compute_text_embedding


def test_question_similarity_relationship_taxonomy():
    # Exact duplicate
    rel, meta, _ = classify_relationship(
        cosine_score=0.995,
        q_a_hash="abc",
        q_b_hash="abc",
        same_topic=True,
        same_type=True,
        diff_a="medium",
        diff_b="medium",
    )
    assert rel == "exact_duplicate"
    assert meta == 1.0

    # Difficulty variation
    rel2, _, _ = classify_relationship(
        cosine_score=0.84,
        q_a_hash="h1",
        q_b_hash="h2",
        same_topic=True,
        same_type=True,
        diff_a="easy",
        diff_b="hard",
    )
    assert rel2 == "difficulty_variation"

    # Paraphrase
    rel3, _, _ = classify_relationship(
        cosine_score=0.82,
        q_a_hash="h1",
        q_b_hash="h2",
        same_topic=False,
        same_type=True,
        diff_a="medium",
        diff_b="medium",
    )
    assert rel3 == "paraphrase"


def test_embedding_similarity_relevance():
    v1 = compute_text_embedding("Find the discriminant of quadratic equation 2x^2 - 4x + 3 = 0")
    v2 = compute_text_embedding("Determine the nature of roots using discriminant of quadratic equation 3x^2 - 5x + 2 = 0")
    v3 = compute_text_embedding("State the role of bile juice and trypsin in human digestion")
    assert len(v1) == 384
    assert cosine_similarity(v1, v2) > cosine_similarity(v1, v3)


def test_exam_dna_trends_and_pattern_change(client, db_session):
    cbse = db_session.query(Exam).filter(Exam.code == "CBSE_10").first()
    math = db_session.query(Subject).filter(Subject.code == "MATH_10").first()
    jee = db_session.query(Exam).filter(Exam.code == "JEE_MAIN").first()
    phy = db_session.query(Subject).filter(Subject.code == "PHY").first()

    # Verified CBSE Class 10 Math DNA
    dna = client.get(f"/api/v1/analytics/exam-dna?exam_id={cbse.id}&subject_id={math.id}")
    assert dna.status_code == 200
    body = dna.json()
    assert body["has_data"] is True
    assert body["total_analyzed_papers"] >= 3
    assert body["total_verified_questions"] >= 20
    assert len(body["chapter_weightage"]) > 0
    assert len(body["sources"]) >= 3

    # Empty state for un-ingested exam (no fabricated statistics)
    empty_dna = client.get(f"/api/v1/analytics/exam-dna?exam_id={jee.id}&subject_id={phy.id}")
    assert empty_dna.status_code == 200
    assert empty_dna.json()["has_data"] is False
    assert empty_dna.json()["total_verified_questions"] == 0

    # Trend comparison 2022 vs 2024
    trends = client.get(
        f"/api/v1/analytics/yearly-trends?exam_id={cbse.id}&subject_id={math.id}&year_a=2022&year_b=2024"
    )
    assert trends.status_code == 200
    assert trends.json()["has_data"] is True
    assert trends.json()["competency_shift_pct"] > 0

    # Pattern change detector (2022-23 -> 2024-25 + rationalised Constructions removal)
    pat = client.get(f"/api/v1/analytics/pattern-changes?exam_id={cbse.id}&subject_id={math.id}")
    assert pat.status_code == 200
    categories = {c["change_category"] for c in pat.json()["changes"]}
    assert "competency_distribution" in categories
    assert "syllabus_topics_removed" in categories
