"""
transformations — SQL Transformation Layer for the Transit Pipeline.

Architecture Reference (Node G → H):
─────────────────────────────────────
  E["Clean Data"] → G["dbt / SQL Transformations"] → H["Analytics Tables"]

This package provides SQL model execution following the dbt-style layered pattern:
  1. Staging    (stg_*)  — Clean, typed views of raw source tables
  2. Intermediate (int_*) — Business logic joins and aggregations
  3. Marts     (mart_*)  — Final analytics tables for dashboards

Usage:
    from transformations import run_all_transformations
    results = run_all_transformations()
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("transformations")

# Directory containing .sql model files
MODELS_DIR = Path(__file__).parent / "models"


# ═══════════════════════════════════════════════════════════════════════════════
# SQL Model Registry (execution order matters)
# ═══════════════════════════════════════════════════════════════════════════════

MODEL_MANIFEST = [
    # ── Layer 1: Staging ──────────────────────────────────────────────────────
    {"name": "stg_vehicles",        "layer": "staging",      "file": "staging/stg_vehicles.sql"},
    {"name": "stg_events",          "layer": "staging",      "file": "staging/stg_events.sql"},
    {"name": "stg_trips",           "layer": "staging",      "file": "staging/stg_trips.sql"},

    # ── Layer 2: Intermediate ─────────────────────────────────────────────────
    {"name": "int_vehicle_delays",  "layer": "intermediate", "file": "intermediate/int_vehicle_delays.sql"},
    {"name": "int_stop_performance","layer": "intermediate", "file": "intermediate/int_stop_performance.sql"},
    {"name": "int_route_stats",     "layer": "intermediate", "file": "intermediate/int_route_stats.sql"},

    # ── Layer 3: Marts (Analytics Tables) ─────────────────────────────────────
    {"name": "mart_hourly_analytics","layer": "marts",       "file": "marts/mart_hourly_analytics.sql"},
    {"name": "mart_route_leaderboard","layer": "marts",      "file": "marts/mart_route_leaderboard.sql"},
    {"name": "mart_daily_summary",   "layer": "marts",       "file": "marts/mart_daily_summary.sql"},
]


def _get_db_connection():
    """Get database connection using the project's config."""
    try:
        from config import DB_PATH
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    except Exception:
        # Fallback for standalone testing
        import database as db
        return db.get_connection()


def run_model(model: Dict[str, str], conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Execute a single SQL transformation model.

    Returns dict with model name, layer, rows affected, and execution time.
    """
    sql_path = MODELS_DIR / model["file"]

    if not sql_path.exists():
        logger.warning("Model file not found: %s — skipping", sql_path)
        return {
            "name": model["name"],
            "layer": model["layer"],
            "status": "skipped",
            "rows_affected": 0,
            "duration_ms": 0,
            "error": f"File not found: {sql_path}",
        }

    sql = sql_path.read_text(encoding="utf-8").strip()
    if not sql:
        return {
            "name": model["name"],
            "layer": model["layer"],
            "status": "skipped",
            "rows_affected": 0,
            "duration_ms": 0,
            "error": "Empty SQL file",
        }

    t0 = time.perf_counter()
    try:
        # Execute the SQL (may contain multiple statements)
        conn.executescript(sql)
        conn.commit()

        # Try to count rows in the resulting table/view
        rows = 0
        try:
            result = conn.execute(f"SELECT COUNT(*) FROM {model['name']}").fetchone()
            rows = result[0] if result else 0
        except Exception:
            pass  # Table might be a CTE or temporary

        elapsed_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            "✅ %s (%s) — %d rows in %.1fms",
            model["name"], model["layer"], rows, elapsed_ms,
        )
        return {
            "name": model["name"],
            "layer": model["layer"],
            "status": "success",
            "rows_affected": rows,
            "duration_ms": round(elapsed_ms, 1),
            "error": None,
        }

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.error("❌ %s (%s) FAILED: %s", model["name"], model["layer"], exc)
        return {
            "name": model["name"],
            "layer": model["layer"],
            "status": "failed",
            "rows_affected": 0,
            "duration_ms": round(elapsed_ms, 1),
            "error": str(exc),
        }


def run_all_transformations() -> Dict[str, Any]:
    """
    Execute all SQL transformation models in dependency order.

    Returns summary dict with total models run, rows affected, and per-model results.
    """
    conn = _get_db_connection()
    results: List[Dict] = []
    total_rows = 0
    failures = 0

    logger.info("━" * 60)
    logger.info("Starting SQL Transformation Pipeline (%d models)", len(MODEL_MANIFEST))
    logger.info("━" * 60)

    t_start = time.perf_counter()

    for model in MODEL_MANIFEST:
        result = run_model(model, conn)
        results.append(result)
        total_rows += result["rows_affected"]
        if result["status"] == "failed":
            failures += 1

    total_ms = (time.perf_counter() - t_start) * 1000
    conn.close()

    summary = {
        "models_run": len(results),
        "models_succeeded": len(results) - failures,
        "models_failed": failures,
        "total_rows_affected": total_rows,
        "total_duration_ms": round(total_ms, 1),
        "model_results": results,
        "executed_at": datetime.now().isoformat(),
    }

    logger.info("━" * 60)
    logger.info(
        "Transformation complete — %d/%d models succeeded, %d rows, %.1fms",
        summary["models_succeeded"], summary["models_run"],
        total_rows, total_ms,
    )
    logger.info("━" * 60)

    return summary


def get_transformation_status() -> List[Dict[str, Any]]:
    """
    Check the current state of all transformation models (table existence, row counts).
    Useful for the Pipeline Health dashboard.
    """
    conn = _get_db_connection()
    status = []

    for model in MODEL_MANIFEST:
        entry = {
            "name": model["name"],
            "layer": model["layer"],
            "sql_file": model["file"],
            "exists": False,
            "row_count": 0,
        }
        try:
            result = conn.execute(f"SELECT COUNT(*) FROM {model['name']}").fetchone()
            entry["exists"] = True
            entry["row_count"] = result[0] if result else 0
        except Exception:
            pass
        status.append(entry)

    conn.close()
    return status


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if "--status" in sys.argv:
        print("\n📊 Transformation Model Status")
        print("─" * 50)
        for s in get_transformation_status():
            icon = "✅" if s["exists"] else "⬜"
            print(f"  {icon} {s['layer']:>14} / {s['name']:<28} — {s['row_count']:>6} rows")
        print()
    else:
        results = run_all_transformations()
        print(f"\n{'═' * 50}")
        print(f"  Models: {results['models_succeeded']}/{results['models_run']} succeeded")
        print(f"  Rows:   {results['total_rows_affected']}")
        print(f"  Time:   {results['total_duration_ms']:.1f}ms")
        print(f"{'═' * 50}")
