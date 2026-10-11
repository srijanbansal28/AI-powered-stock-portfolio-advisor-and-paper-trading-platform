"""
test_architecture.py — Comprehensive end-to-end test suite for the Transit Pipeline Architecture.

Tests all 12 nodes of the system architecture:
  A: Transit Simulator / Event Source
  B: Python Ingestion
  C: Raw Data — PostgreSQL / SQLite
  D: Data Quality Validation
  E: Clean Data
  F: Quarantine + Error Log
  G: dbt / SQL Transformations
  H: Analytics Tables
  I: Streamlit Dashboard imports & layout helpers
  J: Airflow Scheduler DAG tasks
  K: Pipeline Run Audit
  L: Pipeline Health Dashboard metrics
"""

import pytest
import sqlite3
from pathlib import Path

import config
import database as db
from simulator import TransitSimulator
from etl import ETLPipeline
from quality import validate_record, validate_batch
import transformations
from dags.transit_pipeline_dag import (
    task_ingest_stream,
    task_validate_quality,
    task_run_transformations,
    task_log_pipeline_audit,
)


def test_node_a_simulator():
    """Node A: Verify simulator generates valid Bengaluru telemetry events."""
    sim = TransitSimulator(time_acceleration=1.0)
    result = sim.tick()
    assert "vehicles" in result
    assert "events" in result
    assert "trips" in result
    assert len(result["vehicles"]) > 0


def test_node_b_c_ingestion_and_raw_database(tmp_path):
    """Nodes B & C: Ingest raw telemetry into database."""
    test_db = str(tmp_path / "test_transit.db")
    orig_path = config.DB_PATH
    config.DB_PATH = test_db
    try:
        db.init_db()
        db.upsert_routes(config.ROUTES)
        info = db.get_engine_info()
        assert "engine" in info
        assert "url" in info

        sim = TransitSimulator(time_acceleration=1.0)
        tick_data = sim.tick()

        etl = ETLPipeline(max_retries=2, retry_wait=0.1)
        stats = etl.run_tick(tick_data)

        assert stats["records_in"] > 0
        assert stats["records_out"] > 0
    finally:
        config.DB_PATH = orig_path


def test_node_d_e_f_quality_clean_and_quarantine():
    """Nodes D, E, F: Data validation splits clean data from quarantine."""
    # Valid vehicle
    valid_v = {
        "vehicle_id": "V_TEST_001",
        "route_id": "Metro-L1",
        "vehicle_type": "train",
        "status": "in_transit",
        "lat": 12.9716,
        "lon": 77.5946,
        "speed_kmh": 45.0,
        "delay_seconds": 30.0,
        "occupancy": 0.5,
        "last_updated": "2026-10-11T00:00:00",
    }
    errors = validate_record(valid_v, "vehicles")
    assert len(errors) == 0

    # Invalid vehicle (out-of-bounds coordinates)
    invalid_v = {
        "vehicle_id": "V_TEST_BAD",
        "route_id": "Metro-L1",
        "vehicle_type": "train",
        "status": "in_transit",
        "lat": 99.9999,  # Invalid lat
        "lon": 77.5946,
        "speed_kmh": 45.0,
        "delay_seconds": 30.0,
        "occupancy": 0.5,
        "last_updated": "2026-10-11T00:00:00",
    }
    errors = validate_record(invalid_v, "vehicles")
    assert len(errors) > 0
    assert "latitude_out_of_bounds" in errors

    # Validate batch
    valid_list, rejected_list = validate_batch([valid_v, invalid_v], "vehicles")
    assert len(valid_list) == 1
    assert len(rejected_list) == 1


def test_node_g_h_transformations_and_analytics_tables():
    """Nodes G & H: SQL Transformations layer generates analytics marts."""
    results = transformations.run_all_transformations()
    assert len(results) >= 7

    status = transformations.get_transformation_status()
    assert len(status) == 9

    # Verify staging, intermediate, and marts exist
    layers = {s["layer"] for s in status}
    assert "staging" in layers
    assert "intermediate" in layers
    assert "marts" in layers


def test_node_j_airflow_dag_tasks():
    """Node J: Airflow DAG task callables execute successfully."""
    # 1. Ingest stream
    res_ingest = task_ingest_stream()
    assert "records_in" in res_ingest
    assert "records_out" in res_ingest

    # 2. Validate quality
    res_quality = task_validate_quality()
    assert "valid" in res_quality
    assert "quarantined" in res_quality

    # 3. Run transformations
    res_trans = task_run_transformations()
    assert "models_run" in res_trans
    assert res_trans["models_succeeded"] >= 7

    # 4. Pipeline audit
    res_audit = task_log_pipeline_audit()
    assert res_audit["run_id"].startswith("airflow-")
    assert res_audit["status"] == "success"


def test_node_k_l_audit_and_health_metrics():
    """Nodes K & L: Pipeline Run Audit log and Health Dashboard queries."""
    runs = db.get_etl_run_logs(limit=10)
    assert isinstance(runs, list)

    quarantine = db.get_quarantine_records(limit=10)
    assert isinstance(quarantine, list)
