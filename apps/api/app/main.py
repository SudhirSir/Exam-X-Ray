from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.paths import ensure_python_paths

ensure_python_paths()

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.routers import (
    admin,
    analytics,
    auth,
    diagnostics,
    exams,
    papers,
    questions,
    students,
    teacher,
)

settings = get_settings()
configure_logging(debug=settings.DEBUG)
logger = get_logger("api")

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("exam_xray_api_starting", env=settings.APP_ENV)
    yield
    logger.info("exam_xray_api_stopping")


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description=(
        "Production-oriented AI-Powered Examination Intelligence Platform "
        "powered by PySpark, Delta Lake, PostgreSQL/pgvector, and OR-Tools."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception):
    logger.error("unhandled_api_error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": settings.APP_NAME, "version": "1.0.0"}


for router_module in (
    auth.router,
    exams.router,
    analytics.router,
    questions.router,
    diagnostics.router,
    students.router,
    papers.router,
    teacher.router,
    admin.router,
):
    app.include_router(router_module, prefix=settings.API_V1_PREFIX)
