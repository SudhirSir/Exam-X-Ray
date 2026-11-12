from __future__ import annotations

from datetime import datetime, timedelta

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except ImportError:  # Allows importing/syntax-checking outside Airflow container
    DAG = None
    PythonOperator = None


def _run_bronze_silver_gold(**_context):
    from app.core.paths import ensure_python_paths

    ensure_python_paths()
    from app.core.database import SessionLocal
    from pipelines.medallion_runner import execute_medallion_from_db

    db = SessionLocal()
    try:
        run, summary = execute_medallion_from_db(db, trigger_type="airflow_scheduled")
        if run.status != "completed" or not run.dq_passed:
            raise RuntimeError(f"Medallion pipeline failed or DQ check failed: {run.error_message}")
        return {
            "run_id": str(run.id),
            "records_in": run.records_in,
            "records_out": run.records_out,
            "gold_tables": summary.gold_tables if summary else {},
        }
    finally:
        db.close()


def _refresh_question_clusters(**_context):
    from app.core.paths import ensure_python_paths

    ensure_python_paths()
    from app.core.database import SessionLocal
    from app.models.core_exam import ExamSubject
    from intelligence.question_similarity.engine import cluster_questions_for_subject

    db = SessionLocal()
    try:
        pairs = db.query(ExamSubject).all()
        total_clusters = 0
        for es in pairs:
            clusters = cluster_questions_for_subject(db, es.exam_id, es.subject_id)
            total_clusters += len(clusters)
        return {"clusters_refreshed": total_clusters}
    finally:
        db.close()


if DAG is not None:
    default_args = {
        "owner": "exam-xray-data-eng",
        "depends_on_past": False,
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    }

    with DAG(
        dag_id="exam_xray_medallion_pipeline",
        default_args=default_args,
        description="Scheduled PySpark Bronze/Silver/Gold Medallion Pipeline & Question Clustering",
        schedule_interval="0 */6 * * *",
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["exam-xray", "pyspark", "delta-lake", "medallion"],
    ) as dag:
        medallion_task = PythonOperator(
            task_id="run_pyspark_medallion",
            python_callable=_run_bronze_silver_gold,
        )

        cluster_task = PythonOperator(
            task_id="refresh_question_clusters",
            python_callable=_refresh_question_clusters,
        )

        medallion_task >> cluster_task
