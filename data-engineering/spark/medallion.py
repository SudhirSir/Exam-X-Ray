from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

from app.core.config import get_settings
from spark.session import get_spark_session

settings = get_settings()

BRONZE_QUESTION_SCHEMA = StructType(
    [
        StructField("question_id", StringType(), False),
        StructField("paper_id", StringType(), False),
        StructField("exam_id", StringType(), False),
        StructField("exam_code", StringType(), False),
        StructField("subject_id", StringType(), False),
        StructField("subject_code", StringType(), False),
        StructField("syllabus_version_id", StringType(), True),
        StructField("year", IntegerType(), False),
        StructField("set_code", StringType(), False),
        StructField("question_number", StringType(), False),
        StructField("section_name", StringType(), True),
        StructField("question_text", StringType(), False),
        StructField("question_type", StringType(), False),
        StructField("marks", DoubleType(), False),
        StructField("difficulty", StringType(), False),
        StructField("is_competency_based", BooleanType(), False),
        StructField("chapter_name", StringType(), True),
        StructField("topic_id", StringType(), True),
        StructField("topic_name", StringType(), True),
        StructField("content_hash", StringType(), False),
        StructField("verification_status", StringType(), False),
        StructField("confidence_score", DoubleType(), False),
        StructField("data_origin", StringType(), False),
        StructField("source_reference", StringType(), True),
        StructField("cluster_id", StringType(), True),
        StructField("ingested_at", StringType(), False),
    ]
)

BRONZE_ACTIVITY_SCHEMA = StructType(
    [
        StructField("event_id", StringType(), False),
        StructField("analytics_pseudo_id", StringType(), False),
        StructField("exam_id", StringType(), True),
        StructField("subject_id", StringType(), True),
        StructField("topic_id", StringType(), True),
        StructField("chapter_name", StringType(), True),
        StructField("topic_name", StringType(), True),
        StructField("is_correct", BooleanType(), False),
        StructField("time_spent_seconds", IntegerType(), False),
        StructField("difficulty", StringType(), True),
        StructField("occurred_at", StringType(), False),
    ]
)


@dataclass
class MedallionRunSummary:
    run_id: str
    delta_enabled: bool
    records_bronze: int
    records_silver: int
    duplicates_removed: int
    dq_passed: bool
    dq_report: dict[str, Any]
    gold_tables: dict[str, int]
    duration_seconds: float
    spark_app_id: str


def _empty_spark_df(spark: SparkSession, schema: StructType) -> DataFrame:
    type_map = {
        "int": "INT",
        "integer": "INT",
        "bigint": "BIGINT",
        "double": "DOUBLE",
        "float": "FLOAT",
        "boolean": "BOOLEAN",
        "string": "STRING",
    }
    select_exprs = [
        f"CAST(NULL AS {type_map.get(f.dataType.simpleString(), 'STRING')}) AS `{f.name}`"
        for f in schema.fields
    ]
    return spark.sql(f"SELECT {', '.join(select_exprs)}").where("1 = 0")


def _create_spark_df(
    spark: SparkSession, rows: list[dict[str, Any]], schema: StructType | None = None
) -> DataFrame:
    if not rows:
        if schema is None:
            raise ValueError("Schema is required for empty DataFrame creation.")
        return _empty_spark_df(spark, schema)
    pdf = pd.DataFrame(rows)
    if schema is not None:
        cols = [f.name for f in schema.fields]
        for c in cols:
            if c not in pdf.columns:
                pdf[c] = None
        pdf = pdf[cols]
        return spark.createDataFrame(pdf, schema=schema)
    return spark.createDataFrame(pdf)


def _is_windows_hadoop_io_error(exc: Exception) -> bool:
    msg = str(exc)
    return os.name == "nt" and (
        "HADOOP_HOME" in msg
        or "winutils" in msg
        or "NativeIO$Windows" in msg
        or "UnsatisfiedLinkError" in msg
    )


def _spark_to_pyarrow_table(df: DataFrame) -> pa.Table:
    rows = [r.asDict(recursive=True) for r in df.collect()]
    if not rows:
        fields = []
        for sf in df.schema.fields:
            tname = sf.dataType.simpleString()
            if tname in ("int", "bigint"):
                fields.append(pa.field(sf.name, pa.int64(), nullable=True))
            elif tname in ("double", "float"):
                fields.append(pa.field(sf.name, pa.float64(), nullable=True))
            elif tname == "boolean":
                fields.append(pa.field(sf.name, pa.bool_(), nullable=True))
            else:
                fields.append(pa.field(sf.name, pa.string(), nullable=True))
        return pa.Table.from_pylist([], schema=pa.schema(fields))
    return pa.Table.from_pylist(rows)


def _has_windows_hadoop() -> bool:
    if os.name != "nt":
        return True
    hadoop_home = os.environ.get("HADOOP_HOME")
    return bool(hadoop_home and (Path(hadoop_home) / "bin" / "winutils.exe").exists())


def _write_table(
    spark: SparkSession,
    df: DataFrame,
    path: Path,
    delta_enabled: bool,
    mode: str = "overwrite",
    partition_by: list[str] | None = None,
    merge_key: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt = "delta" if delta_enabled else "parquet"

    if delta_enabled and merge_key and mode == "merge" and (path / "_delta_log").exists():
        from delta.tables import DeltaTable

        delta_tbl = DeltaTable.forPath(spark, str(path))
        (
            delta_tbl.alias("target")
            .merge(df.alias("source"), f"target.{merge_key} = source.{merge_key}")
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )
        return

    if _has_windows_hadoop():
        try:
            writer = df.write.format(fmt).mode("overwrite" if mode == "merge" else mode)
            if partition_by:
                writer = writer.partitionBy(*partition_by)
            writer.save(str(path))
            return
        except Exception as exc:
            if not _is_windows_hadoop_io_error(exc):
                raise

    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    table = _spark_to_pyarrow_table(df)
    if partition_by and table.num_rows > 0:
        pdf = table.to_pandas()
        for keys, sub_pdf in pdf.groupby(partition_by, sort=False):
            key_tuple = keys if isinstance(keys, tuple) else (keys,)
            part_dir = path
            for col_name, col_val in zip(partition_by, key_tuple):
                part_dir = part_dir / f"{col_name}={col_val}"
            part_dir.mkdir(parents=True, exist_ok=True)
            sub_table = pa.Table.from_pandas(
                sub_pdf.drop(columns=partition_by), preserve_index=False
            )
            pq.write_table(sub_table, str(part_dir / "part-00000.parquet"))
    else:
        pq.write_table(table, str(path / "part-00000.parquet"))


def _read_table(
    spark: SparkSession,
    path: Path,
    delta_enabled: bool,
    schema: StructType | None = None,
) -> DataFrame:
    fmt = "delta" if (delta_enabled and (path / "_delta_log").exists()) else "parquet"
    if _has_windows_hadoop():
        try:
            return spark.read.format(fmt).load(str(path))
        except Exception as exc:
            if not _is_windows_hadoop_io_error(exc):
                raise
    table = pq.read_table(str(path))
    pdf = table.to_pandas()
    # Normalize categorical partition columns back to primitive types
    for col_name in pdf.columns:
        if isinstance(pdf[col_name].dtype, pd.CategoricalDtype):
            cats = pdf[col_name].cat.categories
            if len(cats) > 0 and pd.api.types.is_integer_dtype(cats.dtype):
                pdf[col_name] = pdf[col_name].astype("int64")
            else:
                pdf[col_name] = pdf[col_name].astype(str)
    if pdf.empty:
        return _empty_spark_df(spark, schema or BRONZE_QUESTION_SCHEMA)
    if schema is not None:
        for f in schema.fields:
            if f.name not in pdf.columns:
                pdf[f.name] = None
        pdf = pdf[[f.name for f in schema.fields]]
    return spark.createDataFrame(pdf, schema=schema)


def run_medallion_pipeline(
    question_records: list[dict[str, Any]],
    topic_records: list[dict[str, Any]],
    activity_records: list[dict[str, Any]] | None = None,
    base_dir: Path | None = None,
) -> MedallionRunSummary:
    """
    Executes the full Bronze -> Silver -> Gold PySpark Medallion pipeline.
    Generates all 9 Gold tables + Data Quality validation report.
    Idempotent via content_hash deduplication and Delta MERGE / overwrite semantics.
    """
    t0 = time.perf_counter()
    run_id = str(uuid.uuid4())
    root = Path(base_dir or settings.MEDALLION_BASE_DIR)
    bronze_dir = root / "bronze"
    silver_dir = root / "silver"
    gold_dir = root / "gold"

    spark, delta_enabled = get_spark_session()
    app_id = spark.sparkContext.applicationId

    now_iso = datetime.now(timezone.utc).isoformat()
    normalized_inputs: list[dict[str, Any]] = []
    for r in question_records:
        normalized_inputs.append(
            {
                "question_id": str(r["question_id"]),
                "paper_id": str(r["paper_id"]),
                "exam_id": str(r["exam_id"]),
                "exam_code": str(r.get("exam_code") or "CBSE_10"),
                "subject_id": str(r["subject_id"]),
                "subject_code": str(r.get("subject_code") or "MATH"),
                "syllabus_version_id": str(r["syllabus_version_id"]) if r.get("syllabus_version_id") else None,
                "year": int(r["year"]),
                "set_code": str(r.get("set_code") or "Main"),
                "question_number": str(r.get("question_number") or "1"),
                "section_name": r.get("section_name"),
                "question_text": str(r["question_text"]),
                "question_type": str(r.get("question_type") or "short_answer"),
                "marks": float(r.get("marks") or 1.0),
                "difficulty": str(r.get("difficulty") or "medium"),
                "is_competency_based": bool(r.get("is_competency_based", False)),
                "chapter_name": r.get("chapter_name"),
                "topic_id": str(r["topic_id"]) if r.get("topic_id") else None,
                "topic_name": r.get("topic_name"),
                "content_hash": str(r["content_hash"]),
                "verification_status": str(r.get("verification_status") or "pending"),
                "confidence_score": float(r.get("confidence_score") or 0.9),
                "data_origin": str(r.get("data_origin") or "verified_official"),
                "source_reference": r.get("source_reference"),
                "cluster_id": str(r["cluster_id"]) if r.get("cluster_id") else None,
                "ingested_at": str(r.get("ingested_at") or now_iso),
            }
        )

    bronze_df = _create_spark_df(spark, normalized_inputs, schema=BRONZE_QUESTION_SCHEMA)

    # BRONZE WRITE (partitioned by exam_code, year)
    bronze_q_path = bronze_dir / "questions"
    _write_table(
        spark,
        bronze_df,
        bronze_q_path,
        delta_enabled=delta_enabled,
        mode="overwrite",
        partition_by=["exam_code", "year"] if normalized_inputs else None,
    )
    records_bronze = bronze_df.count()

    # SILVER TRANSFORMATIONS
    bronze_loaded = _read_table(spark, bronze_q_path, delta_enabled, schema=BRONZE_QUESTION_SCHEMA)

    # 1. Text normalization & missing-value handling
    silver_clean = (
        bronze_loaded.withColumn(
            "normalized_text",
            F.trim(F.regexp_replace(F.lower(F.col("question_text")), r"\s+", " ")),
        )
        .withColumn(
            "difficulty",
            F.when(F.col("difficulty").isin("easy", "medium", "hard"), F.col("difficulty")).otherwise("medium"),
        )
        .withColumn(
            "difficulty_score",
            F.when(F.col("difficulty") == "easy", F.lit(1.0))
            .when(F.col("difficulty") == "medium", F.lit(2.0))
            .otherwise(F.lit(3.0)),
        )
        .withColumn("chapter_name", F.coalesce(F.col("chapter_name"), F.lit("Unmapped Chapter")))
        .withColumn("topic_name", F.coalesce(F.col("topic_name"), F.lit("General Concept")))
        .withColumn("marks", F.when(F.col("marks") > 0, F.col("marks")).otherwise(F.lit(1.0)))
    )

    # 2. Subject/Topic enrichment join if syllabus topics provided
    if topic_records:
        topic_rows = [
            {
                "topic_id": str(t["id"]),
                "official_chapter": str(t["chapter_name"]),
                "official_topic": str(t["topic_name"]),
                "official_weightage_marks": float(t.get("official_weightage_marks") or 0.0),
                "importance_score": float(t.get("importance_score") or 0.5),
            }
            for t in topic_records
        ]
        topics_df = _create_spark_df(spark, topic_rows)
        silver_clean = (
            silver_clean.join(F.broadcast(topics_df), on="topic_id", how="left")
            .withColumn("chapter_name", F.coalesce(F.col("official_chapter"), F.col("chapter_name")))
            .withColumn("topic_name", F.coalesce(F.col("official_topic"), F.col("topic_name")))
            .drop("official_chapter", "official_topic")
        )
    else:
        silver_clean = silver_clean.withColumn("official_weightage_marks", F.lit(0.0)).withColumn(
            "importance_score", F.lit(0.5)
        )

    # 3. Exact duplicate detection per (exam_id, subject_id, year, set_code, content_hash)
    dedup_window = Window.partitionBy(
        "exam_id", "subject_id", "year", "set_code", "content_hash"
    ).orderBy(F.col("confidence_score").desc(), F.col("ingested_at").desc())

    silver_dedup = (
        silver_clean.withColumn("rn", F.row_number().over(dedup_window))
        .filter(F.col("rn") == 1)
        .drop("rn")
    )

    # 4. Data Quality Checks
    total_before_dq = silver_dedup.count()
    invalid_null_text = silver_dedup.filter(
        F.col("normalized_text").isNull() | (F.length(F.col("normalized_text")) < 5)
    ).count()
    invalid_marks = silver_dedup.filter((F.col("marks") <= 0) | (F.col("marks") > 50)).count()
    invalid_year = silver_dedup.filter((F.col("year") < 2000) | (F.col("year") > 2035)).count()
    dq_passed = (invalid_null_text == 0) and (invalid_marks == 0) and (invalid_year == 0)

    silver_valid = silver_dedup.filter(
        F.col("normalized_text").isNotNull()
        & (F.length(F.col("normalized_text")) >= 5)
        & (F.col("marks") > 0)
        & (F.col("marks") <= 50)
        & (F.col("year") >= 2000)
        & (F.col("year") <= 2035)
    )

    silver_q_path = silver_dir / "questions_clean"
    _write_table(
        spark,
        silver_valid,
        silver_q_path,
        delta_enabled=delta_enabled,
        mode="merge" if delta_enabled else "overwrite",
        merge_key="question_id",
    )
    records_silver = silver_valid.count()
    duplicates_removed = max(0, records_bronze - total_before_dq)

    dq_report = {
        "records_bronze": records_bronze,
        "records_after_dedup": total_before_dq,
        "records_silver_valid": records_silver,
        "duplicates_removed": duplicates_removed,
        "invalid_null_text": invalid_null_text,
        "invalid_marks": invalid_marks,
        "invalid_year": invalid_year,
        "dq_passed": dq_passed,
    }

    # GOLD LAYER (Spark SQL + Window Functions)
    silver_valid.createOrReplaceTempView("silver_questions")

    # 1. exam_year_metrics
    exam_year_metrics_df = spark.sql(
        """
        SELECT
            exam_id,
            subject_id,
            year,
            COUNT(DISTINCT paper_id) AS papers_count,
            COUNT(question_id) AS questions_count,
            ROUND(SUM(marks), 2) AS total_marks,
            ROUND(AVG(difficulty_score), 3) AS avg_difficulty_score,
            ROUND(
                100.0 * SUM(CASE WHEN is_competency_based THEN 1 ELSE 0 END) / GREATEST(COUNT(question_id), 1),
                2
            ) AS competency_share_pct
        FROM silver_questions
        GROUP BY exam_id, subject_id, year
        ORDER BY year ASC
        """
    )

    # 2. chapter_weightage (with Window function calculating % share per exam+subject)
    chapter_raw = spark.sql(
        """
        SELECT
            exam_id,
            subject_id,
            chapter_name,
            COUNT(question_id) AS question_count,
            ROUND(SUM(marks), 2) AS total_marks,
            ROUND(AVG(difficulty_score), 3) AS avg_difficulty_score
        FROM silver_questions
        GROUP BY exam_id, subject_id, chapter_name
        """
    )
    subj_win = Window.partitionBy("exam_id", "subject_id")
    chapter_weightage_df = chapter_raw.withColumn(
        "subject_total_marks", F.sum("total_marks").over(subj_win)
    ).withColumn(
        "weightage_pct",
        F.round(
            F.lit(100.0) * F.col("total_marks") / F.greatest(F.col("subject_total_marks"), F.lit(1.0)),
            2,
        ),
    )

    # 3. question_type_distribution
    qtype_raw = spark.sql(
        """
        SELECT
            exam_id,
            subject_id,
            question_type,
            COUNT(question_id) AS question_count,
            ROUND(SUM(marks), 2) AS total_marks
        FROM silver_questions
        GROUP BY exam_id, subject_id, question_type
        """
    )
    question_type_distribution_df = qtype_raw.withColumn(
        "total_q", F.sum("question_count").over(subj_win)
    ).withColumn(
        "share_pct",
        F.round(
            F.lit(100.0) * F.col("question_count") / F.greatest(F.col("total_q"), F.lit(1)), 2
        ),
    )

    # 4. difficulty_distribution
    diff_raw = spark.sql(
        """
        SELECT
            exam_id,
            subject_id,
            difficulty,
            COUNT(question_id) AS question_count,
            ROUND(SUM(marks), 2) AS total_marks
        FROM silver_questions
        GROUP BY exam_id, subject_id, difficulty
        """
    )
    difficulty_distribution_df = diff_raw.withColumn(
        "total_q", F.sum("question_count").over(subj_win)
    ).withColumn(
        "share_pct",
        F.round(
            F.lit(100.0) * F.col("question_count") / F.greatest(F.col("total_q"), F.lit(1)), 2
        ),
    )

    # 5. question_clusters (aggregated from cluster_id or chapter+question_type structural buckets)
    question_clusters_df = spark.sql(
        """
        SELECT
            exam_id,
            subject_id,
            COALESCE(cluster_id, CONCAT(chapter_name, '::', question_type)) AS cluster_key,
            chapter_name,
            question_type,
            COUNT(question_id) AS question_count,
            ROUND(AVG(marks), 2) AS avg_marks,
            COLLECT_SET(year) AS years_appeared
        FROM silver_questions
        GROUP BY exam_id, subject_id, COALESCE(cluster_id, CONCAT(chapter_name, '::', question_type)), chapter_name, question_type
        """
    )

    # 6. topic_trends (year-over-year topic/chapter marks + lag window)
    topic_year_df = spark.sql(
        """
        SELECT
            exam_id,
            subject_id,
            chapter_name,
            topic_name,
            year,
            COUNT(question_id) AS question_count,
            ROUND(SUM(marks), 2) AS total_marks
        FROM silver_questions
        GROUP BY exam_id, subject_id, chapter_name, topic_name, year
        """
    )
    trend_win = Window.partitionBy("exam_id", "subject_id", "chapter_name", "topic_name").orderBy("year")
    topic_trends_df = topic_year_df.withColumn(
        "prev_year_marks", F.lag("total_marks").over(trend_win)
    ).withColumn(
        "marks_delta",
        F.round(F.col("total_marks") - F.coalesce(F.col("prev_year_marks"), F.col("total_marks")), 2),
    )

    # 7. pattern_changes (year-over-year competency & question-type shifts)
    year_type_df = spark.sql(
        """
        SELECT
            exam_id,
            subject_id,
            year,
            question_type,
            COUNT(question_id) AS question_count,
            ROUND(SUM(marks), 2) AS total_marks
        FROM silver_questions
        GROUP BY exam_id, subject_id, year, question_type
        """
    )
    pat_win = Window.partitionBy("exam_id", "subject_id", "question_type").orderBy("year")
    pattern_changes_df = year_type_df.withColumn(
        "prev_question_count", F.lag("question_count").over(pat_win)
    ).withColumn(
        "count_delta",
        F.col("question_count") - F.coalesce(F.col("prev_question_count"), F.col("question_count")),
    )

    # 8 & 9. student_topic_mastery & revision_priorities (from pseudonymous activity events)
    act_rows = activity_records or []
    act_df = _create_spark_df(spark, act_rows, schema=BRONZE_ACTIVITY_SCHEMA)

    _write_table(spark, act_df, bronze_dir / "student_activity_events", delta_enabled=delta_enabled)
    act_df.createOrReplaceTempView("bronze_activity")

    student_topic_mastery_df = spark.sql(
        """
        SELECT
            analytics_pseudo_id,
            exam_id,
            subject_id,
            topic_id,
            COALESCE(chapter_name, 'General') AS chapter_name,
            COALESCE(topic_name, 'General') AS topic_name,
            COUNT(event_id) AS attempts_count,
            ROUND(100.0 * SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) / GREATEST(COUNT(event_id), 1), 2) AS accuracy_pct,
            ROUND(AVG(time_spent_seconds), 2) AS avg_time_seconds,
            ROUND(
                (1.0 - (SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) / GREATEST(COUNT(event_id), 1))),
                3
            ) AS vulnerability_index
        FROM bronze_activity
        GROUP BY analytics_pseudo_id, exam_id, subject_id, topic_id, chapter_name, topic_name
        """
    )

    revision_priorities_df = student_topic_mastery_df.join(
        chapter_weightage_df.select("exam_id", "subject_id", "chapter_name", "weightage_pct"),
        on=["exam_id", "subject_id", "chapter_name"],
        how="left",
    ).withColumn(
        "priority_score",
        F.round(
            F.col("vulnerability_index") * F.lit(0.65)
            + (F.coalesce(F.col("weightage_pct"), F.lit(10.0)) / F.lit(100.0)) * F.lit(0.35),
            4,
        ),
    )

    gold_datasets: dict[str, DataFrame] = {
        "exam_year_metrics": exam_year_metrics_df,
        "chapter_weightage": chapter_weightage_df,
        "question_type_distribution": question_type_distribution_df,
        "question_clusters": question_clusters_df,
        "difficulty_distribution": difficulty_distribution_df,
        "topic_trends": topic_trends_df,
        "pattern_changes": pattern_changes_df,
        "student_topic_mastery": student_topic_mastery_df,
        "revision_priorities": revision_priorities_df,
    }

    gold_counts: dict[str, int] = {}
    for name, gdf in gold_datasets.items():
        gpath = gold_dir / name
        _write_table(spark, gdf, gpath, delta_enabled=delta_enabled, mode="overwrite")
        # Also materialize a lightweight JSON snapshot for instant low-latency API reads
        rows_json = [row.asDict(recursive=True) for row in gdf.collect()]
        snapshot_path = gold_dir / f"{name}.snapshot.json"
        snapshot_path.write_text(json.dumps(rows_json, default=str), encoding="utf-8")
        gold_counts[name] = len(rows_json)

    duration = round(time.perf_counter() - t0, 3)
    return MedallionRunSummary(
        run_id=run_id,
        delta_enabled=delta_enabled,
        records_bronze=records_bronze,
        records_silver=records_silver,
        duplicates_removed=duplicates_removed,
        dq_passed=dq_passed,
        dq_report=dq_report,
        gold_tables=gold_counts,
        duration_seconds=duration,
        spark_app_id=app_id,
    )


def load_gold_snapshot(table_name: str, base_dir: Path | None = None) -> list[dict[str, Any]]:
    root = Path(base_dir or settings.MEDALLION_BASE_DIR)
    snap = root / "gold" / f"{table_name}.snapshot.json"
    if not snap.exists():
        return []
    return json.loads(snap.read_text(encoding="utf-8"))
