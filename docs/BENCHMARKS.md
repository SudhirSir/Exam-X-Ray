# EXAM X-RAY — PySpark Medallion vs. Pandas Benchmark Report

This document records observed performance results from running [benchmark.py](file:///d:/Projects/Exam-X-Ray/data-engineering/spark/benchmark.py) on synthetic load-test data (`5,000` exam questions across 7 academic years, 8 chapters, 5 question formats, and 3 difficulty tiers).

> [!NOTE]
> All numbers below come directly from executing `.\.venv\Scripts\python.exe data-engineering/spark/benchmark.py` on Windows 11 (`local[*]`, Spark 4.1.1 via JDK 23, Parquet storage with PyArrow fallback in absence of `winutils.exe`).

## Observed Results (5,000 Questions)

| Pipeline / Metric | Pandas Baseline | PySpark Medallion (`local[*]`) |
| --- | --- | --- |
| **Input Rows** | 5,000 | 5,000 |
| **Total Wall Time** | **0.057 s** | **34.592 s** |
| **Storage Layer Written** | None (in-memory only) | Partitioned Bronze + Silver + 9 Gold Parquet tables + JSON snapshots |
| **Bronze Records** | — | 5,000 |
| **Silver Valid Records** | 5,000 (deduped) | 5,000 |
| **Duplicates Removed** | 0 | 0 |
| **Data Quality Checks (`dq_passed`)** | Not executed | `true` (null text, marks bounds, year bounds) |
| **Delta Lake Enabled** | N/A | `false` (offline Maven Ivy fallback to Parquet) |

### Gold Layer Output Row Counts (Produced in Same 34.592 s Run)

| Gold Table | Row Count |
| --- | --- |
| `exam_year_metrics` | 7 |
| `chapter_weightage` | 8 |
| `question_type_distribution` | 5 |
| `question_clusters` | 40 |
| `difficulty_distribution` | 3 |
| `topic_trends` | 56 |
| `pattern_changes` | 35 |
| `student_topic_mastery` | 0 *(no synthetic student activity events supplied in default benchmark)* |
| `revision_priorities` | 0 |

## Engineering Analysis

1. **JVM Startup & Serialization Fixed Cost**: At 5,000 rows, Pandas finishes in `0.057 s` because data stays purely in RAM with zero JVM startup, no Parquet disk writes across Bronze/Silver/Gold stages, and only 3 minimal group-bys. PySpark's `34.592 s` includes local JVM initialization, Arrow transfer, Bronze partitioned disk writes (`exam_code` × `year`), Silver read-back + broadcast topic join + Window deduplication + 3 DQ count passes, and materializing all 9 Gold tables + JSON API snapshots.
2. **Why PySpark Scales for Production**: Once question banks + student `LearningActivityEvent` streams grow into millions of rows across multi-state cohorts, single-node Pandas runs hit memory ceilings (`MemoryError`), whereas the PySpark Medallion pipeline partitions cleanly by `exam_code`/`year`, uses Spark SQL + Catalyst optimization + Delta ACID `MERGE` in Linux/Docker deployments, and computes all 9 Gold tables + DQ audits idempotently.
3. **Reproducing Locally**:
   ```powershell
   .\.venv\Scripts\python.exe data-engineering/spark/benchmark.py
   ```
