"""
etl.py — Self-Healing ETL Engine for the Transit Pipeline.

Provides:
  1. retry()       – decorator for automatic retries with exponential back-off
  2. Checkpoint    – persist resume position to disk (survive crashes)
  3. ETLRunLog     – record every job run in SQLite (start/finish/fail)
  4. ETLPipeline   – orchestrates extract→validate→load with all healing layers
  5. Analytics     – get_run_log(), get_etl_health() for dashboard display

Concepts demonstrated
─────────────────────
• Retries          : exponential back-off on transient errors
• Idempotency      : deduplicate by natural key before insert
• Checkpoints      : resume a batch from last committed offset
• Exception logging: every failure stored in etl_run_log table
• Quarantine       : invalid records routed to data_quarantine
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
import sqlite3
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from config import DB_PATH
import database as db
from quality import validate_batch

logger = logging.getLogger("etl")


# ─────────────────────────────────────────────────────────────────────────────
# 1. RETRY — exponential back-off decorator
# ─────────────────────────────────────────────────────────────────────────────

class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    def __init__(self, attempts: int, last_exc: Exception):
        super().__init__(f"All {attempts} attempts failed. Last error: {last_exc}")
        self.attempts = attempts
        self.last_exc = last_exc


def retry(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    backoff_factor: float = 2.0,
    max_wait: float = 30.0,
    retryable: Tuple[type, ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
):
    """
    Decorator that retries a function on failure with exponential back-off.

    Args:
        max_attempts:   Total attempts before giving up (default 3).
        initial_wait:   Seconds to wait after first failure (default 1.0).
        backoff_factor: Multiplier applied to wait time each retry (default 2.0).
        max_wait:       Maximum wait between retries in seconds (default 30).
        retryable:      Exception types that trigger a retry (default all).
        on_retry:       Optional callback(attempt_number, exception) called before each retry.

    Example
    -------
    @retry(max_attempts=5, initial_wait=0.5, retryable=(sqlite3.OperationalError,))
    def save_to_db(records):
        db.upsert_vehicles_bulk(records)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            wait = initial_wait
            last_exc: Exception = RuntimeError("No attempts made")
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    if on_retry:
                        on_retry(attempt, exc)
                    logger.warning(
                        "[retry] %s | attempt %d/%d failed: %s — retrying in %.1fs",
                        func.__name__, attempt, max_attempts, exc, wait,
                    )
                    time.sleep(wait)
                    wait = min(wait * backoff_factor, max_wait)
            raise RetryError(max_attempts, last_exc)
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# 2. CHECKPOINT — persist resume position to survive crashes
# ─────────────────────────────────────────────────────────────────────────────

class Checkpoint:
    """
    Persist and restore ETL progress so a job can resume after failure.

    State is stored as JSON in a small file next to the database.

    Usage
    -----
    cp = Checkpoint("ingest_vehicles")
    offset = cp.get("offset", default=0)       # load last committed position
    for i, batch in enumerate(all_batches):
        if i < offset:
            continue                            # skip already-processed batches
        process(batch)
        cp.save("offset", i + 1)               # commit progress after each batch
    cp.clear()                                  # done — remove checkpoint file
    """

    _dir = Path(DB_PATH).parent / ".etl_checkpoints"

    def __init__(self, job_name: str):
        self.job_name = job_name
        self._path = self._dir / f"{job_name}.json"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._state: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    data = json.load(f)
                logger.info("[checkpoint] Resumed '%s' from previous run", self.job_name)
                return data
            except (json.JSONDecodeError, OSError):
                logger.warning("[checkpoint] Corrupt checkpoint for '%s'; starting fresh.", self.job_name)
        return {}

    def _flush(self) -> None:
        with open(self._path, "w") as f:
            json.dump(self._state, f, indent=2, default=str)

    def get(self, key: str, default: Any = None) -> Any:
        """Return saved value for key, or default if not found."""
        return self._state.get(key, default)

    def save(self, key: str, value: Any) -> None:
        """Persist a single checkpoint value immediately to disk."""
        self._state[key] = value
        self._state["_updated_at"] = datetime.now().isoformat()
        self._flush()

    def update(self, mapping: Dict[str, Any]) -> None:
        """Persist multiple values atomically."""
        self._state.update(mapping)
        self._state["_updated_at"] = datetime.now().isoformat()
        self._flush()

    def clear(self) -> None:
        """Delete the checkpoint file (call on successful job completion)."""
        if self._path.exists():
            self._path.unlink()
        self._state = {}
        logger.info("[checkpoint] Cleared '%s'", self.job_name)

    @property
    def exists(self) -> bool:
        return self._path.exists()


# ─────────────────────────────────────────────────────────────────────────────
# 3. ETL RUN LOG — record every job run in the database
# ─────────────────────────────────────────────────────────────────────────────

class ETLRunLog:
    """
    Record ETL job runs (start, end, status, errors) in etl_run_log table.

    Status lifecycle:  'running'  ->  'success' | 'failed' | 'partial'

    Usage
    -----
    run = ETLRunLog.start("ingest_vehicles")
    try:
        process()
        run.finish(records_in=200, records_out=198, records_rejected=2)
    except Exception as exc:
        run.fail(str(exc), exc)
    """

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS etl_run_log (
        run_id            TEXT    PRIMARY KEY,
        job_name          TEXT    NOT NULL,
        status            TEXT    NOT NULL,
        started_at        TEXT    NOT NULL,
        finished_at       TEXT,
        duration_s        REAL,
        records_in        INTEGER DEFAULT 0,
        records_out       INTEGER DEFAULT 0,
        records_rejected  INTEGER DEFAULT 0,
        retry_count       INTEGER DEFAULT 0,
        error_message     TEXT,
        error_traceback   TEXT,
        metadata_json     TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_etl_run_job  ON etl_run_log(job_name);
    CREATE INDEX IF NOT EXISTS idx_etl_run_stat ON etl_run_log(status);
    """

    def __init__(self, run_id: str, job_name: str, started_at: datetime):
        self.run_id      = run_id
        self.job_name    = job_name
        self.started_at  = started_at
        self.retry_count = 0

    @classmethod
    def _ensure_table(cls) -> None:
        conn = db.get_connection()
        conn.executescript(cls._SCHEMA)
        conn.commit()
        conn.close()

    @classmethod
    def start(cls, job_name: str, metadata: Optional[Dict] = None) -> "ETLRunLog":
        """Insert a new 'running' run record and return the log handle."""
        cls._ensure_table()
        run_id  = str(uuid.uuid4())
        started = datetime.now()
        conn = db.get_connection()
        conn.execute(
            """INSERT INTO etl_run_log
               (run_id, job_name, status, started_at, metadata_json)
               VALUES (?,?,?,?,?)""",
            (run_id, job_name, "running", started.isoformat(),
             json.dumps(metadata) if metadata else None),
        )
        conn.commit()
        conn.close()
        logger.info("[run_log] ▶ Job '%s' started (run_id=%s…)", job_name, run_id[:8])
        return cls(run_id, job_name, started)

    def finish(
        self,
        records_in: int = 0,
        records_out: int = 0,
        records_rejected: int = 0,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Update run to 'success' or 'partial' (if records were rejected)."""
        status = "partial" if records_rejected > 0 else "success"
        now    = datetime.now()
        dur_s  = (now - self.started_at).total_seconds()
        conn   = db.get_connection()
        conn.execute(
            """UPDATE etl_run_log SET
               status=?, finished_at=?, duration_s=?,
               records_in=?, records_out=?, records_rejected=?,
               retry_count=?, metadata_json=?
               WHERE run_id=?""",
            (status, now.isoformat(), dur_s,
             records_in, records_out, records_rejected,
             self.retry_count,
             json.dumps(metadata) if metadata else None,
             self.run_id),
        )
        conn.commit()
        conn.close()
        icon = "✅" if status == "success" else "⚠️"
        logger.info(
            "[run_log] %s Job '%s' %s in %.2fs | in=%d out=%d rejected=%d retries=%d",
            icon, self.job_name, status, dur_s,
            records_in, records_out, records_rejected, self.retry_count,
        )

    def fail(self, error: str, exc: Optional[Exception] = None) -> None:
        """Update run to 'failed' with full error details."""
        now   = datetime.now()
        dur_s = (now - self.started_at).total_seconds()
        tb    = traceback.format_exc() if exc else None
        conn  = db.get_connection()
        conn.execute(
            """UPDATE etl_run_log SET
               status='failed', finished_at=?, duration_s=?,
               retry_count=?, error_message=?, error_traceback=?
               WHERE run_id=?""",
            (now.isoformat(), dur_s, self.retry_count, str(error), tb, self.run_id),
        )
        conn.commit()
        conn.close()
        logger.error("[run_log] ❌ Job '%s' FAILED in %.2fs | retries=%d | %s",
                     self.job_name, dur_s, self.retry_count, error)

    def increment_retry(self) -> None:
        self.retry_count += 1


# ─────────────────────────────────────────────────────────────────────────────
# 4. IDEMPOTENCY — deduplicate by natural key
# ─────────────────────────────────────────────────────────────────────────────

def deduplicate(records: List[Dict], key_field: str) -> Tuple[List[Dict], int]:
    """
    Remove duplicate records from a batch using the record's natural key.

    If the same key appears multiple times the LAST value wins (most recent).
    Returns (deduplicated_list, duplicate_count).

    Example
    -------
    vehicles, dupes = deduplicate(raw_vehicles, key_field="vehicle_id")
    """
    seen: Dict[str, Dict] = {}
    for rec in records:
        key = rec.get(key_field)
        seen[key] = rec          # later record overwrites earlier one
    dupes = len(records) - len(seen)
    return list(seen.values()), dupes


# ─────────────────────────────────────────────────────────────────────────────
# 5. QUARANTINE — route bad records to data_quarantine table
# ─────────────────────────────────────────────────────────────────────────────

def quarantine_records(rejected: List[Dict]) -> int:
    """
    Write rejected records into the data_quarantine table.
    Returns number of records written.
    """
    if not rejected:
        return 0
    rows = [
        {
            "record_type": r["record_type"],
            "record_json": json.dumps(r["record"], default=str),
            "errors_json": json.dumps(r["errors"]),
        }
        for r in rejected
    ]
    conn = db.get_connection()
    conn.executemany(
        """INSERT INTO data_quarantine (record_type, record_json, errors_json)
           VALUES (:record_type, :record_json, :errors_json)""",
        rows,
    )
    conn.commit()
    conn.close()
    logger.warning("[quarantine] %d record(s) quarantined", len(rows))
    return len(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 6. ETLPipeline — the self-healing orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class ETLPipeline:
    """
    Self-healing ETL orchestrator that processes each simulation tick.

    For each tick's data it:
      1. Validates all records       (quality.validate_batch)
      2. Quarantines invalid records (data_quarantine table)
      3. Deduplicates valid records  (by natural key)
      4. Persists to SQLite          (with auto-retry on DB errors)
      5. Logs every run              (etl_run_log table)
      6. Writes checkpoints          (so partial failures can resume)

    Usage (replaces pipeline._persist)
    -----------------------------------
    etl = ETLPipeline(max_retries=3)
    stats = etl.run_tick(result)
    # stats = {records_in, records_out, records_rejected, retries}
    """

    #: Pipeline stages: (record_type, natural_key, db_loader)
    _STAGES = [
        ("vehicles", "vehicle_id", db.upsert_vehicles_bulk),
        ("trips",    "trip_id",    db.upsert_trips_bulk),
        ("events",   None,         db.insert_events_bulk),
    ]

    def __init__(
        self,
        max_retries: int = 3,
        retry_wait:  float = 0.5,
        batch_size:  int = 500,
    ):
        self.max_retries = max_retries
        self.retry_wait  = retry_wait
        self.batch_size  = batch_size
        ETLRunLog._ensure_table()
        logger.info("[ETLPipeline] Ready — max_retries=%d, batch_size=%d",
                    max_retries, batch_size)

    # ── Public API ────────────────────────────────────────────────────────

    def run_tick(self, result: Dict) -> Dict[str, int]:
        """
        Process one simulation tick through the full ETL pipeline.
        Returns stats: {records_in, records_out, records_rejected, retries}.
        """
        run  = ETLRunLog.start("tick_ingest",
                               metadata={"sim_time": str(result.get("sim_time"))})
        cp   = Checkpoint("tick_ingest")
        stats: Dict[str, int] = {
            "records_in": 0, "records_out": 0,
            "records_rejected": 0, "retries": 0,
        }

        try:
            for record_type, key_field, loader in self._STAGES:

                # ── Resume from checkpoint ──────────────────────────────
                if cp.get(f"{record_type}_done"):
                    logger.debug("[ETL] '%s' already committed — skipping (checkpoint)",
                                 record_type)
                    continue

                raw = result.get(record_type, [])
                stats["records_in"] += len(raw)

                # ── Step 1: Validate ────────────────────────────────────
                valid, rejected = validate_batch(raw, record_type)

                # ── Step 2: Quarantine invalid records ──────────────────
                if rejected:
                    n_q = quarantine_records(rejected)
                    stats["records_rejected"] += n_q

                # ── Step 3: Deduplicate (events have no natural key) ────
                if key_field and valid:
                    valid, dupes = deduplicate(valid, key_field)
                    if dupes:
                        logger.debug("[ETL] %d duplicate %s removed before insert",
                                     dupes, record_type)

                # ── Step 4: Persist with retry ──────────────────────────
                written = self._persist_with_retry(
                    record_type, valid, loader, run, stats
                )
                stats["records_out"] += written

                # ── Step 5: Commit checkpoint for this stage ────────────
                cp.save(f"{record_type}_done", True)

            # All stages done
            run.finish(
                records_in=stats["records_in"],
                records_out=stats["records_out"],
                records_rejected=stats["records_rejected"],
                metadata={"retries": stats["retries"]},
            )
            cp.clear()

        except Exception as exc:
            run.fail(str(exc), exc)
            # Checkpoint survives so the next tick can skip completed stages
            logger.error("[ETLPipeline] Tick failed: %s", exc)

        return stats

    # ── Internal helpers ──────────────────────────────────────────────────

    def _persist_with_retry(
        self,
        record_type: str,
        records: List[Dict],
        loader: Callable,
        run: ETLRunLog,
        stats: Dict,
    ) -> int:
        """
        Write records in micro-batches; retry each batch on DB error.
        Permanently failed batches go to quarantine.
        Returns total records successfully written.
        """
        written = 0

        for batch_start in range(0, max(len(records), 1), self.batch_size):
            batch = records[batch_start: batch_start + self.batch_size]
            if not batch:
                continue

            wait    = self.retry_wait
            success = False

            for attempt in range(1, self.max_retries + 1):
                try:
                    loader(batch)
                    written += len(batch)
                    success = True
                    break

                except (sqlite3.OperationalError, sqlite3.DatabaseError) as exc:
                    run.increment_retry()
                    stats["retries"] += 1

                    if attempt >= self.max_retries:
                        logger.error(
                            "[ETL] ❌ %s batch[%d:%d] failed after %d retries: %s",
                            record_type, batch_start,
                            batch_start + len(batch), self.max_retries, exc,
                        )
                        # Permanently failed batch → quarantine
                        quarantine_records([
                            {"record_type": record_type,
                             "record": r,
                             "errors": [f"db_write_error:{exc}"]}
                            for r in batch
                        ])
                        stats["records_rejected"] += len(batch)
                    else:
                        logger.warning(
                            "[ETL] ⚠️  %s batch[%d:%d] attempt %d/%d failed: %s "
                            "— retry in %.1fs",
                            record_type, batch_start, batch_start + len(batch),
                            attempt, self.max_retries, exc, wait,
                        )
                        time.sleep(wait)
                        wait = min(wait * 2.0, 30.0)

        return written


# ─────────────────────────────────────────────────────────────────────────────
# 7. ANALYTICS — query ETL health for the dashboard
# ─────────────────────────────────────────────────────────────────────────────

def get_run_log(limit: int = 100) -> List[Dict]:
    """Return recent ETL run records from etl_run_log."""
    try:
        conn = db.get_connection()
        rows = conn.execute(
            """SELECT run_id, job_name, status, started_at, finished_at,
                      duration_s, records_in, records_out, records_rejected,
                      retry_count, error_message
               FROM etl_run_log
               ORDER BY started_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_quarantine_summary() -> List[Dict]:
    """Return quarantine record counts grouped by record_type."""
    try:
        conn = db.get_connection()
        rows = conn.execute(
            """SELECT record_type, COUNT(*) AS count,
                      MIN(rejected_at) AS first_seen,
                      MAX(rejected_at) AS last_seen
               FROM data_quarantine
               GROUP BY record_type ORDER BY count DESC"""
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_quarantine_records(limit: int = 50) -> List[Dict]:
    """Return raw quarantined records for troubleshooting and dead-letter review."""
    try:
        conn = db.get_connection()
        rows = conn.execute(
            """SELECT quarantine_id, record_type, record_json, errors_json, rejected_at
               FROM data_quarantine
               ORDER BY rejected_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_etl_health() -> Dict:
    """
    Return comprehensive operational metrics for the pipeline health dashboard.

    Keys:
      - total_runs: Total batch execution cycles
      - successful_runs: Runs that completed with status 'success'
      - failed_runs: Runs that terminated abnormally with status 'failed'
      - partial_runs: Runs completed with quarantined records
      - success_rate: Percentage of completed runs without errors
      - rows_ingested: Total rows loaded/persisted to target tables (records_out)
      - rows_received: Total input rows evaluated (records_in)
      - rejected_records: Total records routed to dead-letter quarantine
      - retry_count: Total automated retries performed across all jobs
      - avg_processing_time_ms: Average batch execution time in milliseconds
      - last_processing_time_ms: Most recent execution time in milliseconds
      - last_successful_run: Timestamp of last successful/partial execution
      - last_run_at: Timestamp of most recent execution start
      - last_run_status: Status of the most recent execution ('success', 'failed', etc.)
    """
    try:
        conn = db.get_connection()
        row = conn.execute(
            """SELECT
                COUNT(*)                                                                AS total_runs,
                SUM(CASE WHEN status='failed'  THEN 1 ELSE 0 END)                      AS failed_runs,
                SUM(CASE WHEN status='success' THEN 1 ELSE 0 END)                      AS successful_runs,
                SUM(CASE WHEN status='partial' THEN 1 ELSE 0 END)                      AS partial_runs,
                SUM(COALESCE(retry_count, 0))                                          AS total_retries,
                SUM(COALESCE(records_in, 0))                                           AS rows_received,
                SUM(COALESCE(records_out, 0))                                          AS rows_ingested,
                SUM(COALESCE(records_rejected, 0))                                     AS rejected_records,
                AVG(COALESCE(duration_s, 0)) * 1000.0                                  AS avg_processing_time_ms,
                MAX(CASE WHEN status IN ('success', 'partial') THEN finished_at END)  AS last_successful_run,
                MAX(started_at)                                                        AS last_run_at
               FROM etl_run_log"""
        ).fetchone()

        last = conn.execute(
            """SELECT status, duration_s, started_at
               FROM etl_run_log
               ORDER BY started_at DESC LIMIT 1"""
        ).fetchone()
        conn.close()

        total = row["total_runs"] or 0
        success = (row["successful_runs"] or 0) + (row["partial_runs"] or 0)
        last_dur_ms = (last["duration_s"] * 1000.0) if (last and last["duration_s"] is not None) else 0.0

        return {
            "total_runs":             total,
            "successful_runs":        row["successful_runs"] or 0,
            "failed_runs":            row["failed_runs"] or 0,
            "partial_runs":           row["partial_runs"] or 0,
            "success_rate":           round(success / total * 100, 1) if total else 0.0,
            "rows_ingested":          row["rows_ingested"] or 0,
            "rows_received":          row["rows_received"] or 0,
            "rejected_records":       row["rejected_records"] or 0,
            "retry_count":            row["total_retries"] or 0,
            "avg_processing_time_ms": round(row["avg_processing_time_ms"] or 0.0, 1),
            "last_processing_time_ms": round(last_dur_ms, 1),
            "last_successful_run":    row["last_successful_run"] or "—",
            "last_run_at":            row["last_run_at"] or "—",
            "last_run_status":        last["status"] if last else "—",
        }
    except Exception as exc:
        logger.error("Error reading ETL health summary: %s", exc)
        return {
            "total_runs": 0, "successful_runs": 0, "failed_runs": 0, "partial_runs": 0,
            "success_rate": 0.0, "rows_ingested": 0, "rows_received": 0, "rejected_records": 0,
            "retry_count": 0, "avg_processing_time_ms": 0.0, "last_processing_time_ms": 0.0,
            "last_successful_run": "—", "last_run_at": "—", "last_run_status": "—",
        }
