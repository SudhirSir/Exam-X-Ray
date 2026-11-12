from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]
for p in (str(ROOT_DIR), str(ROOT_DIR / "data-engineering"), str(ROOT_DIR / "apps" / "api")):
    if p not in sys.path:
        sys.path.insert(0, p)

# Set test environment defaults before importing app modules
_TEST_TMP = Path(tempfile.mkdtemp(prefix="exam_xray_test_"))
os.environ["MEDALLION_BASE_DIR"] = str(_TEST_TMP / "medallion")
os.environ["LOCAL_STORAGE_DIR"] = str(_TEST_TMP / "uploads")
os.environ["USE_DELTA_LAKE"] = "false"  # Deterministic local Parquet in tests unless Delta JARs cached

from app.core.database import Base, get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401
from database.seed_data.seed_verified_cbse import seed_verified_cbse_data


@pytest.fixture(scope="session")
def test_engine():
    db_path = _TEST_TMP / "test_exam_xray.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="session")
def TestingSessionLocal(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine, future=True)


@pytest.fixture(scope="session", autouse=True)
def seed_test_db(TestingSessionLocal):
    db = TestingSessionLocal()
    try:
        seed_verified_cbse_data(db, run_embeddings=True)
    finally:
        db.close()


@pytest.fixture()
def db_session(TestingSessionLocal):
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(TestingSessionLocal):
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()
