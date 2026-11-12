from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "EXAM X-RAY"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Security & JWT
    JWT_SECRET_KEY: str = "exam-xray-dev-secret-change-in-production-32bytes"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    CSRF_SECRET_KEY: str = "exam-xray-csrf-dev-secret-change-in-production"

    # Database
    DATABASE_URL: str = f"sqlite:///{(ROOT_DIR / 'exam_xray.db').as_posix()}"
    ENABLE_PGVECTOR: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage
    S3_ENDPOINT: str = ""
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "exam-xray-documents"
    LOCAL_STORAGE_DIR: str = str(ROOT_DIR / "data" / "uploads")

    # Spark & Medallion
    SPARK_MASTER: str = "local[*]"
    SPARK_APP_NAME: str = "ExamXRayMedallion"
    MEDALLION_BASE_DIR: str = str(ROOT_DIR / "data")
    USE_DELTA_LAKE: bool = True
    JAVA_HOME: str = r"C:\Program Files\Java\jdk-23"

    # AI / Embeddings
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    ALLOW_MODEL_DOWNLOAD: bool = False
    USE_TRANSFORMER_EMBEDDINGS: bool = False

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    return Settings()
