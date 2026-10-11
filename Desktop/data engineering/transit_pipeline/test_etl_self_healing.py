"""
test_etl_self_healing.py — Validation test suite for Self-Healing ETL pipeline.
Tests:
  1. Exponential back-off retries on simulated transient failures
  2. Idempotency & deduplication
  3. Checkpoint persistence and resume after crash
  4. Quarantine of malformed or corrupt records
  5. Structured execution run logging (etl_run_log)
"""

import unittest
import sqlite3
from datetime import datetime
from pathlib import Path

import database as db
import etl
from etl import retry, RetryError, Checkpoint, ETLRunLog, ETLPipeline, deduplicate, quarantine_records
from quality import validate_batch


class TestSelfHealingETL(unittest.TestCase):

    def setUp(self):
        db.init_db()

    def test_retry_decorator_succeeds_after_transient_failure(self):
        calls = 0

        @retry(max_attempts=3, initial_wait=0.01, backoff_factor=1.5)
        def flaky_function():
            nonlocal calls
            calls += 1
            if calls < 3:
                raise sqlite3.OperationalError("database is locked")
            return "recovered"

        result = flaky_function()
        self.assertEqual(result, "recovered")
        self.assertEqual(calls, 3)

    def test_retry_decorator_raises_on_exhausted_attempts(self):
        calls = 0

        @retry(max_attempts=3, initial_wait=0.01, backoff_factor=1.5)
        def permanently_broken():
            nonlocal calls
            calls += 1
            raise sqlite3.OperationalError("fatal disk I/O error")

        with self.assertRaises(RetryError) as ctx:
            permanently_broken()
        self.assertEqual(ctx.exception.attempts, 3)
        self.assertEqual(calls, 3)

    def test_idempotent_deduplication(self):
        records = [
            {"vehicle_id": "V1", "speed": 30},
            {"vehicle_id": "V2", "speed": 40},
            {"vehicle_id": "V1", "speed": 35},  # duplicate natural key
            {"vehicle_id": "V3", "speed": 25},
            {"vehicle_id": "V2", "speed": 45},  # duplicate natural key
        ]
        unique, duplicate_count = deduplicate(records, "vehicle_id")
        self.assertEqual(len(unique), 3)
        self.assertEqual(duplicate_count, 2)
        # Should retain the latest record for V1 and V2
        self.assertEqual(next(r["speed"] for r in unique if r["vehicle_id"] == "V1"), 35)
        self.assertEqual(next(r["speed"] for r in unique if r["vehicle_id"] == "V2"), 45)

    def test_checkpoint_persistence_and_resume(self):
        job_name = "test_resilient_job"
        cp = Checkpoint(job_name)
        cp.clear()

        # Step 1: Save progress
        cp.save("stage_1_done", True)
        cp.save("records_processed", 42)

        # Simulate crash and reload checkpoint
        cp_resumed = Checkpoint(job_name)
        self.assertTrue(cp_resumed.get("stage_1_done"))
        self.assertEqual(cp_resumed.get("records_processed"), 42)

        # Step 2: Clear on job completion
        cp_resumed.clear()
        cp_fresh = Checkpoint(job_name)
        self.assertFalse(cp_fresh.exists)
        self.assertIsNone(cp_fresh.get("stage_1_done"))

    def test_data_quarantine(self):
        bad_records = [
            {
                "record_type": "vehicles",
                "record": {"vehicle_id": "MALFORMED_1", "lat": 999.0},
                "errors": ["lat_out_of_bounds"],
            }
        ]
        quarantine_records(bad_records)
        summary = etl.get_quarantine_summary()
        self.assertTrue(any(s["record_type"] == "vehicles" for s in summary))

        recent_q = db.get_quarantine_records(limit=5)
        self.assertTrue(len(recent_q) > 0)

    def test_etl_run_log_lifecycle(self):
        run = ETLRunLog.start("unit_test_job")
        self.assertEqual(run.retry_count, 0)
        run.increment_retry()
        self.assertEqual(run.retry_count, 1)

        run.finish(records_in=50, records_out=48, records_rejected=2)

        logs = etl.get_run_log(limit=5)
        matched = next((l for l in logs if l["run_id"] == run.run_id), None)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["status"], "partial")  # rejected > 0 marks partial
        self.assertEqual(matched["records_in"], 50)
        self.assertEqual(matched["records_out"], 48)
        self.assertEqual(matched["records_rejected"], 2)
        self.assertEqual(matched["retry_count"], 1)

    def test_etl_pipeline_tick_execution(self):
        etl_pipe = ETLPipeline(max_retries=2, retry_wait=0.01)
        mock_tick_result = {
            "vehicles": [
                {
                    "vehicle_id": "TEST_BUS_01",
                    "route_id": "BUS-101",
                    "trip_id": "T1",
                    "vehicle_type": "bus",
                    "status": "in_transit",
                    "current_stop_id": "101_S1",
                    "next_stop_id": "101_S2",
                    "lat": 12.9716,
                    "lon": 77.5946,
                    "speed_kmh": 30.0,
                    "delay_seconds": 10.0,
                    "occupancy": 0.5,
                    "heading": 90.0,
                    "last_updated": datetime.now().isoformat(),
                }
            ],
            "trips": [],
            "events": [],
            "sim_time": datetime.now(),
        }
        stats = etl_pipe.run_tick(mock_tick_result)
        self.assertEqual(stats["records_in"], 1)
        self.assertEqual(stats["records_out"], 1)
        self.assertEqual(stats["records_rejected"], 0)


if __name__ == "__main__":
    unittest.main()
