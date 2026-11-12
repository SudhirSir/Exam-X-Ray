from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename or "document.pdf")
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return cleaned[:180] or "document.pdf"


def validate_pdf_bytes(filename: str, content: bytes) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension '{ext}'. Only PDF files are permitted.")
    if len(content) == 0:
        raise ValueError("Uploaded PDF file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File exceeds maximum allowed size of {MAX_UPLOAD_BYTES // (1024*1024)} MB.")
    if not content[:8].lstrip().startswith(b"%PDF-"):
        raise ValueError("Invalid PDF signature: file header does not start with %PDF-.")


class DocumentStorageService:
    """Stores uploaded PDFs in S3-compatible object storage (MinIO/AWS) or local directory."""

    def __init__(self) -> None:
        self.local_dir = Path(settings.LOCAL_STORAGE_DIR)
        self.local_dir.mkdir(parents=True, exist_ok=True)
        self.s3_endpoint = settings.S3_ENDPOINT.strip()

    def save_document(self, filename: str, content: bytes, file_hash: str) -> str:
        safe_name = sanitize_filename(filename)
        storage_key = f"papers/{file_hash[:12]}_{safe_name}"

        if self.s3_endpoint:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError

            try:
                client = boto3.client(
                    "s3",
                    endpoint_url=self.s3_endpoint,
                    aws_access_key_id=settings.S3_ACCESS_KEY,
                    aws_secret_access_key=settings.S3_SECRET_KEY,
                )
                try:
                    client.head_bucket(Bucket=settings.S3_BUCKET)
                except ClientError:
                    client.create_bucket(Bucket=settings.S3_BUCKET)
                client.put_object(
                    Bucket=settings.S3_BUCKET,
                    Key=storage_key,
                    Body=content,
                    ContentType="application/pdf",
                )
                return f"s3://{settings.S3_BUCKET}/{storage_key}"
            except (BotoCoreError, ClientError):
                # Fall back to local storage if S3 endpoint is configured but unreachable in dev
                pass

        dest = self.local_dir / storage_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        return str(dest)

    def read_document(self, storage_key: str) -> Optional[bytes]:
        if storage_key.startswith("s3://") and self.s3_endpoint:
            import boto3

            _, rest = storage_key.split("s3://", 1)
            bucket, key = rest.split("/", 1)
            client = boto3.client(
                "s3",
                endpoint_url=self.s3_endpoint,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
            )
            obj = client.get_object(Bucket=bucket, Key=key)
            return obj["Body"].read()

        path = Path(storage_key)
        if path.exists():
            return path.read_bytes()
        return None
