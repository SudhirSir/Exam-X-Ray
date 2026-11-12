from __future__ import annotations

import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.models.core_exam import Exam, Subject


def _build_sample_cbse_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 780
    lines = [
        "CBSE CLASS 10 MATHEMATICS SAMPLE PAPER 2025",
        "Section A",
        "1. Find the HCF of 96 and 404 using prime factorization method. [1 mark]",
        "(A) 2  (B) 4  (C) 8  (D) 12",
        "Ans: B",
        "2. If the quadratic equation x^2 - 6x + k = 0 has equal roots, find k. [2 marks]",
        "Section C",
        "3. Prove that sin^2 theta + cos^2 theta = 1 using a right triangle. [3 marks]",
    ]
    for line in lines:
        c.drawString(50, y, line)
        y -= 24
    c.save()
    return buf.getvalue()


def test_e2e_pdf_upload_extract_pyspark_exam_dna(client, db_session):
    """
    Validates Primary Journey #1:
    Admin uploads CBSE PDF -> Extract questions -> PySpark Medallion -> Exam DNA reflects update.
    """
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@examxray.in", "password": "Admin@ExamXRay2026"},
    )
    assert login.status_code == 200

    cbse = db_session.query(Exam).filter(Exam.code == "CBSE_10").first()
    math = db_session.query(Subject).filter(Subject.code == "MATH_10").first()

    pdf_bytes = _build_sample_cbse_pdf()
    upload = client.post(
        "/api/v1/admin/documents/upload",
        data={
            "exam_id": str(cbse.id),
            "subject_id": str(math.id),
            "year": "2025",
            "set_code": "SQP-TEST",
            "auto_verify": "true",
        },
        files={"file": ("cbse_math_2025_test.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload.status_code == 200, upload.text
    res = upload.json()
    assert res["questions_extracted"] >= 3
    assert res["spark_dq_passed"] is True

    # Uploading exact same PDF again must trigger SHA-256 duplicate protection (409)
    dup = client.post(
        "/api/v1/admin/documents/upload",
        data={
            "exam_id": str(cbse.id),
            "subject_id": str(math.id),
            "year": "2025",
            "set_code": "SQP-TEST-2",
        },
        files={"file": ("cbse_math_2025_dup.pdf", pdf_bytes, "application/pdf")},
    )
    assert dup.status_code == 409

    # Exam DNA now uses PySpark Gold snapshot and includes 2025 paper
    dna = client.get(f"/api/v1/analytics/exam-dna?exam_id={cbse.id}&subject_id={math.id}")
    assert dna.status_code == 200
    assert dna.json()["computation_source"] == "gold_spark_delta"
    years = [y["year"] for y in dna.json()["yearly_trends"]]
    assert 2025 in years


def test_e2e_student_diagnostic_xray_and_paper_generator(client, db_session):
    """
    Validates Primary Journey #2:
    Student logs in -> starts diagnostic -> submits answers -> inspects X-Ray report ->
    generates OR-Tools paper -> exports PDF -> attempts online.
    """
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "student@examxray.in", "password": "Student@ExamXRay2026"},
    )
    assert login.status_code == 200

    cbse = db_session.query(Exam).filter(Exam.code == "CBSE_10").first()
    math = db_session.query(Subject).filter(Subject.code == "MATH_10").first()

    # 1. Start diagnostic
    start = client.post(
        "/api/v1/diagnostics/start",
        json={
            "exam_id": str(cbse.id),
            "subject_id": str(math.id),
            "question_count": 6,
            "time_limit_minutes": 15,
        },
    )
    assert start.status_code == 200, start.text
    diag = start.json()
    assert len(diag["questions"]) == 6

    # 2. Submit diagnostic with mixed answers and timing
    answers = []
    for i, q in enumerate(diag["questions"]):
        submitted = q["options"][0]["option_label"] if (i % 2 == 0 and q["options"]) else ""
        answers.append(
            {
                "question_id": q["question_id"],
                "submitted_answer": submitted,
                "time_spent_seconds": 45 if i % 2 == 0 else 190,
            }
        )
    sub = client.post(
        f"/api/v1/diagnostics/{diag['id']}/submit",
        json={"answers": answers},
    )
    assert sub.status_code == 200, sub.text
    xray = sub.json()
    assert xray["status"] == "evaluated"
    assert len(xray["recommendations"]) >= 1
    assert "because" in xray["recommendations"][0]["reason_explanation"].lower()

    # 3. Student mastery & recommendations endpoints populated
    assert client.get("/api/v1/students/me/mastery").json()["has_data"] is True
    assert client.get("/api/v1/students/me/recommendations").json()["has_data"] is True

    # 4. Generate OR-Tools optimized question paper
    gen = client.post(
        "/api/v1/papers/generate",
        json={
            "exam_id": str(cbse.id),
            "subject_id": str(math.id),
            "total_marks": 15,
            "question_count": 7,
            "time_limit_minutes": 45,
        },
    )
    assert gen.status_code == 200, gen.text
    paper = gen.json()
    assert len(paper["questions"]) >= 4
    # Verify no duplicate question IDs
    q_ids = [q["question_id"] for q in paper["questions"]]
    assert len(q_ids) == len(set(q_ids))

    # 5. Export Paper PDF & Answer Key PDF
    pdf_res = client.get(f"/api/v1/papers/{paper['id']}/export?format=paper_pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.content.startswith(b"%PDF-")

    key_res = client.get(f"/api/v1/papers/{paper['id']}/export?format=answer_key_pdf")
    assert key_res.status_code == 200
    assert key_res.content.startswith(b"%PDF-")

    # 6. Attempt paper online
    attempt = client.post(
        f"/api/v1/papers/{paper['id']}/attempt",
        json={
            "time_taken_seconds": 300,
            "answers": {q_ids[0]: "A"},
        },
    )
    assert attempt.status_code == 200
    assert attempt.json()["max_score"] > 0
