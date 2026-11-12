from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class IngestionJobOut(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    subject_id: uuid.UUID
    year: int
    set_code: str
    file_name: str
    file_hash: str
    status: str
    pages_extracted: int
    questions_extracted: int
    question_paper_id: uuid.UUID | None = None
    error_message: str | None = None
    metrics_json: dict[str, Any] | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProcessingRunOut(BaseModel):
    id: uuid.UUID
    pipeline_name: str
    layer: str
    status: str
    trigger_type: str
    records_in: int
    records_out: int
    dq_passed: bool
    dq_report_json: dict[str, Any] | None = None
    duration_seconds: float | None = None
    started_at: datetime
    finished_at: datetime | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}
