from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

import pyspark
from pyspark.sql import SparkSession

from app.core.config import get_settings

settings = get_settings()

JAVA_OPENS = (
    "-Djava.security.manager=allow "
    "--add-opens=java.base/java.lang=ALL-UNNAMED "
    "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED "
    "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED "
    "--add-opens=java.base/java.io=ALL-UNNAMED "
    "--add-opens=java.base/java.net=ALL-UNNAMED "
    "--add-opens=java.base/java.nio=ALL-UNNAMED "
    "--add-opens=java.base/java.util=ALL-UNNAMED "
    "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED "
    "--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED "
    "--add-opens=java.base/javax.security.auth=ALL-UNNAMED "
    "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED "
    "--add-opens=java.base/sun.nio.cs=ALL-UNNAMED "
    "--add-opens=java.base/sun.security.action=ALL-UNNAMED "
    "--add-opens=java.base/sun.util.calendar=ALL-UNNAMED"
)


def _base_builder(app_name: str, warehouse_dir: Path, ivy_dir: Path) -> SparkSession.Builder:
    builder = SparkSession.builder
    # Reset global SparkSession.Builder options left behind by any failed attempt
    if hasattr(builder, "_options") and isinstance(builder._options, dict):
        builder._options.clear()
    return (
        builder.appName(app_name)
        .master(settings.SPARK_MASTER)
        .config("spark.sql.warehouse.dir", str(warehouse_dir))
        .config("spark.jars.ivy", str(ivy_dir))
        .config("spark.driver.extraJavaOptions", JAVA_OPENS)
        .config("spark.executor.extraJavaOptions", JAVA_OPENS)
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.task.maxDirectResultSize", "67108864")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
    )


@lru_cache(maxsize=1)
def get_spark_session(app_name: str | None = None) -> tuple[SparkSession, bool]:
    """
    Create or retrieve a configured PySpark SparkSession.
    Returns (spark_session, delta_enabled).
    """
    # Ensure pip-installed pyspark uses its own matching Spark JARs rather than mismatched host SPARK_HOME
    pyspark_home = str(Path(pyspark.__file__).resolve().parent)
    os.environ["SPARK_HOME"] = pyspark_home
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    os.environ["JDK_JAVA_OPTIONS"] = JAVA_OPENS
    if settings.JAVA_HOME and Path(settings.JAVA_HOME).exists():
        os.environ["JAVA_HOME"] = settings.JAVA_HOME

    base_dir = Path(settings.MEDALLION_BASE_DIR)
    warehouse_dir = base_dir / "warehouse"
    ivy_dir = base_dir / ".ivy2"
    warehouse_dir.mkdir(parents=True, exist_ok=True)
    ivy_dir.mkdir(parents=True, exist_ok=True)

    resolved_app = app_name or settings.SPARK_APP_NAME
    delta_enabled = False

    if settings.USE_DELTA_LAKE:
        try:
            from delta import configure_spark_with_delta_pip

            delta_builder = (
                _base_builder(resolved_app, warehouse_dir, ivy_dir)
                .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
                .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
            )
            spark = configure_spark_with_delta_pip(delta_builder).getOrCreate()
            delta_enabled = True
            spark.sparkContext.setLogLevel("WARN")
            return spark, delta_enabled
        except Exception:
            os.environ.pop("PYSPARK_SUBMIT_ARGS", None)
            delta_enabled = False

    spark = _base_builder(resolved_app, warehouse_dir, ivy_dir).getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark, delta_enabled
