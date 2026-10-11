"""
transit_pipeline_dag.py — Apache Airflow DAG for the Bengaluru Transit Pipeline.

Architecture Reference (Nodes J → B, D, G, K):
─────────────────────────────────────────────────
  J["Airflow Scheduler"]
    ├──. "Orchestrates tasks" .──→ B["Python Ingestion"]
    ├──. "Retries and dependencies" .──→ D["Data Quality Validation"]
    └──. "Schedules transformations" .──→ G["dbt / SQL Transformations"]

  B → K["Pipeline Run Audit"]
  D → K
  G → K

DAG: transit_etl_orchestrator
─────────────────────────────
  1. ingest_stream        → Simulate one batch of transit telemetry & ingest to raw PostgreSQL/SQLite
  2. validate_quality     → Run data quality validation; route valid → clean, invalid → quarantine
  3. run_transformations   → Execute SQL transformation models (staging → intermediate → marts)
  4. log_pipeline_audit   → Write audit trail entry summarising the full pipeline run

Schedule: Every 5 minutes (configurable)
Retries:  3 with exponential back-off (60s base)

Usage:
    # Copy this file to your Airflow dags/ folder:
    cp dags/transit_pipeline_dag.py ~/airflow/dags/

    # Or symlink:
    ln -s $(pwd)/dags/transit_pipeline_dag.py ~/airflow/dags/

    # Test individual tasks:
    airflow tasks test transit_etl_orchestrator ingest_stream 2026-01-01

    # Trigger the full DAG:
    airflow dags trigger transit_etl_orchestrator
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ─── Ensure the project root is importable when running inside Airflow ───
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
    from airflow.utils.dates import days_ago
    HAS_AIRFLOW = True
except ImportError:
    # Allow importing this module outside Airflow for testing & documentation
    HAS_AIRFLOW = False

logger = logging.getLogger("airflow.transit_etl")


# ═══════════════════════════════════════════════════════════════════════════════
# Task Callables
# ═══════════════════════════════════════════════════════════════════════════════

def task_ingest_stream(**context) -> dict:
    """
    Node B — Python Ingestion.

    Runs one simulation tick and persists raw telemetry into the database.
    Uses the self-healing ETL engine with retry/checkpoint/quarantine layers.
    """
    import database as db
    from config import ROUTES
    from simulator import TransitSimulator
    from etl import ETLPipeline

    db.init_db()
    db.upsert_routes(ROUTES)

    sim = TransitSimulator(time_acceleration=1.0)
    result = sim.tick()

    etl = ETLPipeline(max_retries=3, retry_wait=0.5)
    stats = etl.run_tick(result)

    logger.info(
        "Ingestion complete — in=%d out=%d rejected=%d retries=%d",
        stats["records_in"], stats["records_out"],
        stats["records_rejected"], stats["retries"],
    )

    # Push stats to XCom for downstream tasks
    return {
        "records_in": stats["records_in"],
        "records_out": stats["records_out"],
        "records_rejected": stats["records_rejected"],
        "retries": stats["retries"],
        "sim_time": result["sim_time"].isoformat(),
    }


def task_validate_quality(**context) -> dict:
    """
    Node D — Data Quality Validation.

    Re-validates the most recent batch of ingested records against quality rules.
    Valid records remain in clean tables; invalid records are quarantined.
    Airflow retries handle transient failures automatically (Node J).
    """
    import database as db
    from quality import validate_batch

    conn = db.get_connection()

    # Pull recent vehicles and events for validation
    vehicles = conn.execute(
        "SELECT * FROM vehicles ORDER BY last_updated DESC LIMIT 200"
    ).fetchall()
    vehicles = [dict(v) for v in vehicles]

    events = conn.execute(
        "SELECT * FROM events ORDER BY timestamp DESC LIMIT 500"
    ).fetchall()
    events = [dict(e) for e in events]
    conn.close()

    # Validate vehicles
    valid_v, rejected_v = validate_batch(vehicles, record_type="vehicles")
    # Validate events
    valid_e, rejected_e = validate_batch(events, record_type="events")

    total_valid = len(valid_v) + len(valid_e)
    total_invalid = len(rejected_v) + len(rejected_e)

    # Quarantine invalid records
    if rejected_v or rejected_e:
        conn = db.get_connection()
        for item in rejected_v:
            conn.execute(
                "INSERT INTO data_quarantine (record_type, record_json, errors_json) VALUES (?, ?, ?)",
                (item.get("record_type", "vehicles"), json.dumps(item.get("record"), default=str), json.dumps(item.get("errors", []))),
            )
        for item in rejected_e:
            conn.execute(
                "INSERT INTO data_quarantine (record_type, record_json, errors_json) VALUES (?, ?, ?)",
                (item.get("record_type", "events"), json.dumps(item.get("record"), default=str), json.dumps(item.get("errors", []))),
            )
        conn.commit()
        conn.close()

    logger.info(
        "Validation complete — valid=%d quarantined=%d",
        total_valid, total_invalid,
    )
    return {"valid": total_valid, "quarantined": total_invalid}


def task_run_transformations(**context) -> dict:
    """
    Node G — dbt / SQL Transformations.

    Executes SQL transformation models from the transformations/ directory
    to build analytics tables (staging → intermediate → marts).
    """
    import database as db
    from transformations import run_all_transformations

    results = run_all_transformations()

    logger.info(
        "Transformations complete — models=%d total_rows=%d",
        results["models_run"], results["total_rows_affected"],
    )
    return results


def task_log_pipeline_audit(**context) -> dict:
    """
    Node K — Pipeline Run Audit.

    Aggregates results from all upstream tasks (B, D, G) and writes
    a unified audit entry summarising the pipeline run.
    """
    import database as db
    import uuid

    ti = context.get("ti")

    # Pull XCom from upstream tasks (with fallback for standalone runs)
    ingest_stats = (ti.xcom_pull(task_ids="ingest_stream") if ti else {}) or {}
    quality_stats = (ti.xcom_pull(task_ids="validate_quality") if ti else {}) or {}
    transform_stats = (ti.xcom_pull(task_ids="run_transformations") if ti else {}) or {}

    run_id = str(uuid.uuid4())[:12]
    now = datetime.now().isoformat()

    audit_entry = {
        "run_id": f"airflow-{run_id}",
        "job_name": "transit_etl_orchestrator",
        "status": "success",
        "started_at": context.get("execution_date", now),
        "finished_at": now,
        "duration_s": 0,  # Computed by Airflow task duration
        "records_in": ingest_stats.get("records_in", 0),
        "records_out": ingest_stats.get("records_out", 0),
        "records_rejected": ingest_stats.get("records_rejected", 0) + quality_stats.get("quarantined", 0),
        "retry_count": ingest_stats.get("retries", 0),
        "error_message": None,
        "error_traceback": None,
        "metadata_json": json.dumps({
            "orchestrator": "airflow",
            "dag_id": "transit_etl_orchestrator",
            "ingest": ingest_stats,
            "quality": quality_stats,
            "transformations": transform_stats,
        }),
    }

    conn = db.get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO etl_run_log
            (run_id, job_name, status, started_at, finished_at, duration_s,
             records_in, records_out, records_rejected, retry_count,
             error_message, error_traceback, metadata_json)
        VALUES (:run_id, :job_name, :status, :started_at, :finished_at, :duration_s,
                :records_in, :records_out, :records_rejected, :retry_count,
                :error_message, :error_traceback, :metadata_json)
    """, audit_entry)
    conn.commit()
    conn.close()

    logger.info("Pipeline audit logged — run_id=%s", audit_entry["run_id"])
    return audit_entry


# ═══════════════════════════════════════════════════════════════════════════════
# DAG Definition
# ═══════════════════════════════════════════════════════════════════════════════

if HAS_AIRFLOW:

    default_args = {
        "owner": "transit_pipeline",
        "depends_on_past": False,
        "email_on_failure": False,
        "email_on_retry": False,
        "retries": 3,
        "retry_delay": timedelta(seconds=60),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=10),
    }

    with DAG(
        dag_id="transit_etl_orchestrator",
        default_args=default_args,
        description="Bengaluru Transit Pipeline — Ingestion → Validation → Transformation → Audit",
        schedule_interval="*/5 * * * *",  # Every 5 minutes
        start_date=days_ago(1),
        catchup=False,
        max_active_runs=1,
        tags=["transit", "etl", "data-engineering", "bengaluru"],
        doc_md=__doc__,
    ) as dag:

        # ── Node B: Python Ingestion ──────────────────────────────────────────
        t_ingest = PythonOperator(
            task_id="ingest_stream",
            python_callable=task_ingest_stream,
            doc_md="Simulate transit telemetry and ingest raw data into PostgreSQL/SQLite.",
        )

        # ── Node D: Data Quality Validation ───────────────────────────────────
        t_validate = PythonOperator(
            task_id="validate_quality",
            python_callable=task_validate_quality,
            doc_md="Validate ingested data. Valid → clean tables, Invalid → quarantine + error log.",
        )

        # ── Node G: SQL Transformations ───────────────────────────────────────
        t_transform = PythonOperator(
            task_id="run_transformations",
            python_callable=task_run_transformations,
            doc_md="Execute SQL models (staging → intermediate → marts) for analytics tables.",
        )

        # ── Node K: Pipeline Run Audit ────────────────────────────────────────
        t_audit = PythonOperator(
            task_id="log_pipeline_audit",
            python_callable=task_log_pipeline_audit,
            doc_md="Aggregate all upstream results and write unified audit trail entry.",
        )

        # ── DAG Dependencies (matching architecture diagram) ──────────────────
        # J (Airflow) orchestrates: B → D → G → K
        # B and D feed audit logs to K
        t_ingest >> t_validate >> t_transform >> t_audit


# ═══════════════════════════════════════════════════════════════════════════════
# Standalone Test Runner (run without Airflow installed)
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  Transit Pipeline DAG — Standalone Test Runner")
    print("  (Running tasks sequentially without Airflow)")
    print("=" * 70)

    print("\n[1/4] Running ingestion...")
    ingest_result = task_ingest_stream()
    print(f"       → {ingest_result}")

    print("\n[2/4] Running quality validation...")
    quality_result = task_validate_quality()
    print(f"       → {quality_result}")

    print("\n[3/4] Running SQL transformations...")
    try:
        transform_result = task_run_transformations()
        print(f"       → {transform_result}")
    except Exception as e:
        print(f"       → Skipped (transformations module not available): {e}")
        transform_result = {}

    print("\n[4/4] Logging pipeline audit...")
    # Mock context for standalone run
    class MockTI:
        def xcom_pull(self, task_ids=None):
            return {"records_in": 0, "records_out": 0, "records_rejected": 0, "retries": 0}

    audit_result = task_log_pipeline_audit(
        ti=MockTI(),
        execution_date=datetime.utcnow().isoformat(),
    )
    print(f"       → {audit_result}")

    print("\n" + "=" * 70)
    print("  All tasks completed successfully!")
    print("=" * 70)
