from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)
    role: Literal["student", "teacher"] = "student"
    is_minor: bool = False
    guardian_email: EmailStr | None = None
    consent_accepted: bool = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    analytics_pseudo_id: str
    is_minor: bool
    guardian_consent_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserOut
    csrf_token: str
    token_type: str = "cookie"


class ExamProfileRequest(BaseModel):
    exam_id: uuid.UUID
    target_year: int = Field(default=2026, ge=2024, le=2035)
    daily_study_minutes: int = Field(default=60, ge=15, le=720)
    preferred_language: str = "English"
    is_primary: bool = True
