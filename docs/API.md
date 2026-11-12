# EXAM X-RAY — REST API Reference

Base URL: `/api/v1` (OpenAPI schema: `/api/v1/openapi.json`, Swagger UI: `/docs`).
Authentication uses HTTP-only cookies (`access_token`, `refresh_token`) plus `X-CSRF-Token`.

## Health & Auth
- `GET /health` — Service health check.
- `POST /api/v1/auth/register` — Register student/teacher account (enforces `guardian_email` if `is_minor=true`).
- `POST /api/v1/auth/login` — Authenticate and set HTTP-only JWT cookies.
- `POST /api/v1/auth/logout` — Clear auth cookies.
- `POST /api/v1/auth/refresh` — Rotate access/refresh tokens via refresh cookie.
- `GET /api/v1/auth/me` — Current user profile.
- `POST /api/v1/auth/profile/exam` — Set target examination, year, and study budget.
- `GET /api/v1/auth/me/export` — Export personal data snapshot (DPDP compliance).
- `DELETE /api/v1/auth/me` — Soft-delete and anonymize PII.

## Examinations Registry
- `GET /api/v1/exams/bodies` — List examination bodies (`CBSE`, `CISCE`, `NTA`, `UPSC`, `SSC`, `RRB`).
- `GET /api/v1/exams` — List configured exams (`CBSE_10`, `CBSE_12`, `ICSE_10`, `JEE_MAIN`, `NEET_UG`, etc.).
- `POST /api/v1/exams` *(admin)* — Register a new examination via data-driven config.
- `GET /api/v1/exams/{exam_id}` — Get exam details & attached subjects.
- `GET /api/v1/exams/{exam_id}/subjects` — List subjects under an exam.
- `GET /api/v1/exams/{exam_id}/versions` — List academic year versions & blueprints.
- `GET /api/v1/exams/{exam_id}/topics?subject_id=...` — List active syllabus chapters & topics.

## Exam DNA, Trends & Pattern Changes
- `GET /api/v1/analytics/exam-dna?exam_id=...&subject_id=...&year_from=&year_to=` — Full Exam DNA report (only verified non-synthetic records unless `include_synthetic=true`).
- `GET /api/v1/analytics/topic-weightage?exam_id=...&subject_id=...` — Chapter weightage & recurring concepts.
- `GET /api/v1/analytics/yearly-trends?exam_id=...&subject_id=...&year_a=2023&year_b=2024` — Year-over-year weightage, question-type, competency, and difficulty shift analysis with clear disclaimers.
- `GET /api/v1/analytics/pattern-changes?exam_id=...&subject_id=...` — Blueprint diffs & rationalised syllabus additions/removals across exam versions.

## Question DNA & Semantic Intelligence
- `GET /api/v1/questions` — Filter verified bank by exam, subject, year, type, difficulty, verification status.
- `GET /api/v1/questions/search?q=...` — Semantic + metadata search across embedded questions.
- `GET /api/v1/questions/similar?question_id=...` — Related questions labeled with relationship taxonomy (`exact_duplicate`, `paraphrase`, `same_concept`, `same_pattern`, `difficulty_variation`) and confidence scores.
- `GET /api/v1/questions/{question_id}` — Single question details, options, official answer/marking scheme.

## Personal Exam Vulnerability Scanner
- `GET /api/v1/diagnostics/my-tests` — Student's past diagnostic sessions.
- `POST /api/v1/diagnostics/start` — Launch diagnostic test sampled for target exam/subject.
- `POST /api/v1/diagnostics/{diagnostic_id}/submit` — Evaluate answers, classify mistake patterns, propagate prerequisite risk, emit pseudonymous `LearningActivityEvent`, and return full Exam X-Ray report.
- `GET /api/v1/diagnostics/{diagnostic_id}/results` — Retrieve evaluated Exam X-Ray report.
- `GET /api/v1/students/me/mastery` — Student topic mastery & vulnerability scores.
- `GET /api/v1/students/me/vulnerability` — Latest vulnerability summary (explicitly labeled as estimates).
- `GET /api/v1/students/me/recommendations` — Prioritized revision roadmap with *WHY* explanations.
- `GET /api/v1/students/me/progress` — Historical readiness timeline.

## Smart Question Paper Generator
- `POST /api/v1/papers/generate` — Solve constrained paper generation via Google OR-Tools CP-SAT (`total_marks`, `question_count`, chapters, types, difficulty distribution, non-duplication).
- `GET /api/v1/papers` — List user's saved generated papers.
- `GET /api/v1/papers/{paper_id}` — View full generated paper & marking scheme.
- `GET /api/v1/papers/{paper_id}/export?format=paper_pdf|answer_key_pdf|json` — Download printable PDF paper or answer key via ReportLab.
- `POST /api/v1/papers/{paper_id}/attempt` — Submit online attempt for instant grading.

## Teacher & Administration
- `GET /api/v1/teacher/overview` *(teacher/admin)* — Cohort readiness and weakest chapters.
- `GET /api/v1/teacher/students-progress` *(teacher/admin)* — Pseudonymous student progress table.
- `POST /api/v1/admin/documents/upload` *(admin)* — Upload PDF -> SHA-256 deduplicate -> PyMuPDF/OCR extract -> auto-classify -> embed -> run PySpark Medallion.
- `GET /api/v1/admin/ingestion/jobs` *(admin/teacher)* — Document ingestion history.
- `GET /api/v1/admin/processing-runs` *(admin/teacher)* — PySpark Medallion audit history & DQ status.
- `POST /api/v1/admin/pipeline/run` *(admin)* — Manually trigger Bronze -> Silver -> Gold PySpark Medallion run.
- `GET /api/v1/admin/review-queue` *(admin/teacher)* — Pending extracted questions awaiting human QA.
- `POST /api/v1/admin/questions/{question_id}/verify` *(admin/teacher)* — Approve/edit/reject extracted question.
- `GET /api/v1/admin/data-quality` *(admin/teacher)* — Overall verification coverage & latest Spark DQ checks.
