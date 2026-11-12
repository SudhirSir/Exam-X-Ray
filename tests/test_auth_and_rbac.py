from __future__ import annotations

import uuid


def test_register_login_refresh_and_dpdp_export(client):
    email = f"student_{uuid.uuid4().hex[:8]}@test.in"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword@123",
            "full_name": "Kavya Nair",
            "role": "student",
            "is_minor": True,
            "guardian_email": "parent@test.in",
            "consent_accepted": True,
        },
    )
    assert reg.status_code == 201, reg.text
    assert "exam_xray_access_token" in reg.cookies
    assert "exam_xray_refresh_token" in reg.cookies

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["analytics_pseudo_id"].startswith("stu_")

    # Student must be blocked from teacher & admin endpoints
    assert client.get("/api/v1/teacher/overview").status_code == 403
    assert client.post("/api/v1/admin/pipeline/run").status_code == 403

    # Refresh token flow
    ref = client.post("/api/v1/auth/refresh")
    assert ref.status_code == 200

    # DPDP Data export
    exp = client.get("/api/v1/auth/me/export")
    assert exp.status_code == 200
    assert exp.json()["user"]["email"] == email

    # Account self-deletion / anonymization
    dele = client.delete("/api/v1/auth/me")
    assert dele.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_minor_requires_guardian_email(client):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"minor_{uuid.uuid4().hex[:6]}@test.in",
            "password": "StrongPassword@123",
            "full_name": "Young Learner",
            "role": "student",
            "is_minor": True,
            "guardian_email": None,
            "consent_accepted": True,
        },
    )
    assert res.status_code == 400


def test_teacher_and_admin_rbac(client):
    # Login as seeded teacher
    t_login = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher@examxray.in", "password": "Teacher@ExamXRay2026"},
    )
    assert t_login.status_code == 200
    assert client.get("/api/v1/teacher/overview").status_code == 200
    assert client.post("/api/v1/admin/pipeline/run").status_code == 403

    # Login as seeded admin
    a_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@examxray.in", "password": "Admin@ExamXRay2026"},
    )
    assert a_login.status_code == 200
    assert client.get("/api/v1/admin/data-quality").status_code == 200
