# EXAM X-RAY — Verified Examination Import & Curation Workflow

EXAM X-RAY strictly enforces **data provenance**: unverified or synthetic test records never pollute official **Exam DNA** reports or trend comparisons.

## End-to-End Ingestion Lifecycle

1. **Pre-Validation & Deduplication**
   - Upload PDF via `POST /api/v1/admin/documents/upload` (Admin role required).
   - File extension and magic bytes (`%PDF-`) are validated.
   - SHA-256 digest is checked against `question_papers.document_hash`. Exact duplicates are rejected with HTTP `409` and logged as `IngestionJob(status="duplicate")`.

2. **Object Storage & Question Extraction**
   - Raw PDF bytes are stored in S3/MinIO (with local `data/uploads/` fallback when S3 is unconfigured).
   - `data-engineering/ingestion/pdf_extractor.py` parses pages with PyMuPDF (`fitz`) and falls back to `pytesseract` OCR for scanned pages.
   - Question boundaries, section headers, marks allocations, MCQ options (`A`-`D`), and LaTeX/math expressions are extracted with per-question confidence scores.

3. **Auto-Classification, Embeddings & Similarity**
   - Each extracted question is linked to its closest `syllabus_topics` entry via keyword & TF-IDF cosine matching (`assigned_by="nlp_classifier"`).
   - 384-dimensional embeddings (`question_embeddings`) and cluster memberships (`question_clusters`) are updated.
   - Newly extracted questions enter with `verification_status="pending"` (unless `auto_verify=true` is explicitly selected for official board releases) and generate an `ExtractionReview` queue entry.

4. **Human Verification Workbench (`/admin/verification`)**
   - Subject-matter reviewers inspect extracted text, math formulas, marks, difficulty, and assigned topic via `GET /api/v1/admin/review-queue`.
   - Reviewers approve, edit, or reject via `POST /api/v1/admin/questions/{question_id}/verify`.
   - Every decision records an immutable `AuditLog` event (`question_review`).

5. **PySpark Bronze -> Silver -> Gold Medallion Sync**
   - Once verified, trigger `POST /api/v1/admin/pipeline/run` (or wait for the scheduled Apache Airflow DAG `exam_xray_medallion_dag`).
   - Only `is_deleted = false` and `data_origin != 'synthetic_dev'` records enter production Exam DNA Gold tables.

## Separating Development/Synthetic Data

- `database/seed_data/seed_verified_cbse.py` seeds verified CBSE Class 10 Mathematics (Standard) & Science board items (`data_origin='verified_official'`).
- `database/seed_data/seed_dev_synthetic.py` seeds load-test questions explicitly tagged `data_origin='synthetic_dev'`.
- Analytics endpoints (`Exam DNA`, `Trends`, `Paper Generator`) filter to `verified_official` records by default.
