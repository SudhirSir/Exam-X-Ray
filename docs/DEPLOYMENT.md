# EXAM X-RAY — Deployment & Operations Guide

## 1. Docker Compose Stack (Recommended for Production / Staging)

All core infrastructure services run from `infrastructure/docker/docker-compose.yml`:

- `postgres`: `pgvector/pgvector:pg16` (transactional DB + 384-dim `VECTOR` embeddings)
- `redis`: `redis:7-alpine` (rate limiting & caching)
- `minio`: `minio/minio:latest` (S3-compatible PDF/artifact storage on ports `9000`/`9001`)
- `api`: FastAPI + PySpark + OR-Tools + PyMuPDF + Tesseract (`:8000`, auto-runs `alembic upgrade head`)
- `web`: Next.js 15 production server (`:3000`)
- `airflow`: Apache Airflow 2.10.4 scheduler/webserver (`:8080`, mounts `orchestration/airflow/dags`)

### Quick Launch

```bash
cp .env.example .env
# Edit JWT_SECRET_KEY, CSRF_SECRET_KEY, POSTGRES_PASSWORD in .env
docker compose -f infrastructure/docker/docker-compose.yml up --build -d
```

Seed verified CBSE Class 10 data inside the running API container:

```bash
docker compose -f infrastructure/docker/docker-compose.yml exec api python database/seed_data/seed_verified_cbse.py
```

### Dedicated Spark Worker Image

Build the standalone PySpark + Delta Lake worker image when offloading heavy batch jobs from the API container:

```bash
docker build -f infrastructure/docker/Dockerfile.spark -t exam-xray-spark:latest .
```

## 2. Environment Variables

Key variables in `.env.example`:

| Variable | Purpose | Production Recommendation |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy DB URI | `postgresql+psycopg2://...` |
| `ENABLE_PGVECTOR` | Enables `pgvector` extension & `VECTOR(384)` | `true` on PostgreSQL |
| `JWT_SECRET_KEY` / `CSRF_SECRET_KEY` | Cookie signing secrets | High-entropy 32+ byte random hex |
| `COOKIE_SECURE` | Sets `Secure` attribute on auth cookies | `true` behind HTTPS/TLS |
| `S3_ENDPOINT` / `S3_BUCKET` | MinIO or AWS S3 storage | `https://s3...` or `http://minio:9000` |
| `USE_DELTA_LAKE` | Enables Delta ACID ACID/MERGE writes | `true` (falls back to Parquet offline) |
| `ALLOW_MODEL_DOWNLOAD` | Download `all-MiniLM-L6-v2` from HuggingFace | `true` if model not pre-cached |

## 3. Local Development (Windows / Linux without Docker)

1. Activate Python 3.11+ virtual environment with `pip install -r requirements.txt` and JDK 17+ (`JAVA_HOME`).
2. Apply migrations & seed data:
   ```bash
   alembic -c database/migrations/alembic.ini upgrade head
   python database/seed_data/seed_verified_cbse.py
   ```
3. Start FastAPI:
   ```bash
   uvicorn apps.api.app.main:app --app-dir apps/api --host 0.0.0.0 --port 8000
   ```
4. Start Next.js:
   ```bash
   cd apps/web && npm run build && npm run start
   ```
