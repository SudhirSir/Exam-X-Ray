from __future__ import annotations

from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    REFRESH_COOKIE_NAME,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    set_auth_cookies,
    verify_password,
)
from app.models.operations import AuditLog
from app.models.paper_gen import PaperAttempt
from app.models.student import (
    DiagnosticTest,
    StudentExamProfile,
    StudentRecommendation,
    StudentTopicMastery,
    User,
)
from app.schemas.auth import (
    AuthResponse,
    ExamProfileRequest,
    LoginRequest,
    RegisterRequest,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    if payload.is_minor and not payload.guardian_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guardian email is required for minor accounts under data protection policy.",
        )

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
        is_minor=payload.is_minor,
        guardian_email=payload.guardian_email.lower() if payload.guardian_email else None,
        guardian_consent_verified=not payload.is_minor,
        consent_accepted_at=datetime.now(timezone.utc) if payload.consent_accepted else None,
    )
    db.add(user)
    db.flush()
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="user_registered",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=request.client.host if request.client else None,
            details_json={"role": user.role, "is_minor": user.is_minor},
        )
    )
    db.commit()
    db.refresh(user)

    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id), user.role)
    csrf_token = set_auth_cookies(response, access_token, refresh_token)
    return AuthResponse(user=UserOut.model_validate(user), csrf_token=csrf_token)


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == payload.email.lower(), User.is_deleted.is_(False))
        .first()
    )
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id), user.role)
    csrf_token = set_auth_cookies(response, access_token, refresh_token)

    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="user_login",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
    return AuthResponse(user=UserOut.model_validate(user), csrf_token=csrf_token)


@router.post("/logout")
def logout(response: Response):
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=AuthResponse)
def refresh(
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    if not refresh_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing.",
        )
    payload = decode_token(refresh_cookie, expected_type="refresh")
    user_id = uuid.UUID(str(payload["sub"]))
    user = db.query(User).filter(User.id == user_id, User.is_deleted.is_(False)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )
    access_token = create_access_token(str(user.id), user.role)
    new_refresh = create_refresh_token(str(user.id), user.role)
    csrf_token = set_auth_cookies(response, access_token, new_refresh)
    return AuthResponse(user=UserOut.model_validate(user), csrf_token=csrf_token)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.post("/profile/exam")
def upsert_exam_profile(
    payload: ExamProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(StudentExamProfile)
        .filter(
            StudentExamProfile.user_id == current_user.id,
            StudentExamProfile.exam_id == payload.exam_id,
        )
        .first()
    )
    if profile:
        profile.target_year = payload.target_year
        profile.daily_study_minutes = payload.daily_study_minutes
        profile.preferred_language = payload.preferred_language
        profile.is_primary = payload.is_primary
    else:
        profile = StudentExamProfile(
            user_id=current_user.id,
            exam_id=payload.exam_id,
            target_year=payload.target_year,
            daily_study_minutes=payload.daily_study_minutes,
            preferred_language=payload.preferred_language,
            is_primary=payload.is_primary,
        )
        db.add(profile)
    db.commit()
    return {"status": "saved", "exam_id": str(payload.exam_id), "target_year": payload.target_year}


@router.get("/me/export")
def export_my_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """DPDP / privacy compliance: exports all personal records held for the user."""
    profiles = db.query(StudentExamProfile).filter(StudentExamProfile.user_id == current_user.id).all()
    tests = db.query(DiagnosticTest).filter(DiagnosticTest.student_id == current_user.id).all()
    mastery = db.query(StudentTopicMastery).filter(StudentTopicMastery.student_id == current_user.id).all()
    recs = db.query(StudentRecommendation).filter(StudentRecommendation.student_id == current_user.id).all()
    attempts = db.query(PaperAttempt).filter(PaperAttempt.user_id == current_user.id).all()
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "analytics_pseudo_id": current_user.analytics_pseudo_id,
        },
        "exam_profiles": [{"exam_id": str(p.exam_id), "target_year": p.target_year} for p in profiles],
        "diagnostic_tests_count": len(tests),
        "topic_mastery_records": [
            {"topic_id": str(m.topic_id), "accuracy_pct": m.accuracy_pct, "mastery_score": m.mastery_score}
            for m in mastery
        ],
        "recommendations_count": len(recs),
        "paper_attempts_count": len(attempts),
    }


@router.delete("/me")
def delete_my_account(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-deletes and anonymizes user PII while keeping pseudonymous analytical aggregates safe."""
    current_user.is_deleted = True
    current_user.is_active = False
    current_user.deleted_at = datetime.now(timezone.utc)
    current_user.email = f"deleted_{current_user.id}@anonymized.local"
    current_user.full_name = "Deleted User"
    current_user.guardian_email = None
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="user_self_deleted",
            resource_type="user",
            resource_id=str(current_user.id),
        )
    )
    db.commit()
    clear_auth_cookies(response)
    return {"status": "deleted", "message": "Account anonymized and deactivated."}
