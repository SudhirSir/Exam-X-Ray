# EXAM X-RAY

> **Don't Just Prepare. Understand the Examination.**

EXAM X-RAY is a production-oriented, AI-powered Examination Intelligence Platform built with **PySpark**, **Delta Lake**, **PostgreSQL + pgvector**, **FastAPI**, **OR-Tools**, **Scikit-learn / Sentence Transformers**, **Apache Airflow**, and **Next.js App Router**.

It validates and demonstrates its full vertical slice on verified **CBSE Class 10 Mathematics (Standard) & Science** papers while supporting an extensible Indian examination registry (`CBSE 10/12`, `ICSE 10`, `JEE Main`, `NEET UG`, `UPSC CSE`, `SSC CGL`, `RRB NTPC`).

## Core Modules

1. **Exam DNA Analyzer** — Chapter weightage, question-type composition, difficulty distributions, recurring concepts, and verifiable source references backed by the PySpark Medallion Lakehouse.
2. **Question DNA Engine** — 384-dim semantic embeddings (`all-MiniLM-L6-v2` with offline deterministic fallback), KMeans pattern clustering, and multi-tier similarity classification (`exact_duplicate`, `paraphrase`, `same_concept`, `same_pattern`, `difficulty_variation`) with human review workflows.
3. **Exam Trend Intelligence** — Multi-year comparison of chapter weightage, competency-based questions, and difficulty evolution with explicit forecasting disclaimers.
4. **Personal Exam Vulnerability Scanner** — Diagnostic testing with per-question timing, mistake-pattern diagnosis, prerequisite risk propagation, and explainable revision roadmaps (*WHY* each topic is prioritized).
5. **Smart Question Paper Generator** — Google OR-Tools CP-SAT constraint optimization over verified question banks with instant printable Question Paper & Answer Key PDF export (`ReportLab`) plus online practice attempts.
6. **Exam Pattern Change Detector** — Blueprint section changes and rationalised syllabus diffs (added/removed topics across academic versions).

## Repository Structure

```text
apps/
  api/          FastAPI + SQLAlchemy 2.0 + JWT HTTP-only cookies + RBAC
  web/          Next.js 15 App Router + TypeScript + Tailwind + Recharts
data-engineering/
  ingestion/    PDF extraction (PyMuPDF + Tesseract OCR), SHA-256 dedup, S3/local storage
  pipelines/    DB <-> PySpark Medallion runner
  spark/        SparkSession, Bronze/Silver/Gold Medallion pipeline, benchmark
database/
  migrations/   Alembic schema migrations (34 tables)
  seed_data/    Separate verified CBSE seeder & synthetic load-test fixture generator
docs/           Architecture, ER diagram, API reference, Deployment, Benchmarks, Import workflow
infrastructure/ Docker Compose & Dockerfiles (API, Web, Spark, Postgres/pgvector, Redis, MinIO, Airflow)
intelligence/   Six modular analytical & optimization engines
notebooks/      Jupyter exploration notebook for Medallion & Exam DNA datasets
orchestration/  Apache Airflow DAG
tests/          Automated pytest suite (RBAC, PySpark Medallion, Intelligence engines, E2E)
```

## Quick Start (Docker Compose)

```bash
cp .env.example .env
docker compose -f infrastructure/docker/docker-compose.yml up --build -d
docker compose -f infrastructure/docker/docker-compose.yml exec api python database/seed_data/seed_verified_cbse.py
```

- Frontend: `http://localhost:3000`
- Backend API & Docs: `http://localhost:8000/docs`
- Airflow: `http://localhost:8080`
- MinIO Console: `http://localhost:9001`

## Quick Start (Local Development)

```bash
python -m venv .venv
.\.venv\Scripts\activate  # or source .venv/bin/activate
pip install -r requirements.txt
alembic -c database/migrations/alembic.ini upgrade head
python database/seed_data/seed_verified_cbse.py

# Start API
uvicorn apps.api.app.main:app --app-dir apps/api --reload --port 8000

# Start Frontend
cd apps/web && npm install && npm run dev
```

## Demo Accounts (Seeded Verified Dataset)

| Role | Email | Password |
|---|---|---|
| Admin | `admin@examxray.in` | `Admin@ExamXRay2026` |
| Teacher | `teacher@examxray.in` | `Teacher@ExamXRay2026` |
| Student | `student@examxray.in` | `Student@ExamXRay2026` |

## Documentation

- [System Architecture](docs/ARCHITECTURE.md)
- [Database ER Diagram](docs/DATABASE_ER.md)
- [REST API Reference](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Verified Import Workflow](docs/VERIFIED_IMPORT_WORKFLOW.md)
- [PySpark vs. Pandas Benchmarks](docs/BENCHMARKS.md)
