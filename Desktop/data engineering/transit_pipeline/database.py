"""
database.py — Database schema and CRUD helpers for the transit pipeline.

Architecture Reference (Node C):
  B["Python Ingestion"] → C["Raw Data — PostgreSQL"] → D["Data Quality Validation"]

Supports dual-engine connectivity:
  • PostgreSQL — Set DATABASE_URL or POSTGRES_URL environment variable
                  e.g. postgresql://user:pass@localhost:5432/transit
  • SQLite     — Default fallback using config.DB_PATH (WAL mode)

Tables:
  routes             — Static route / stop metadata
  vehicles           — Current vehicle state (position, status)
  trips              — Trip records (scheduled vs actual times)
  events             — High-frequency vehicle location / status stream
  analytics_snapshots— Periodic KPI rollups
  data_quarantine    — Dead-letter queue for invalid records (Node F)
  etl_run_log        — Pipeline execution audit trail (Node K)
"""

import os
import sqlite3
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from config import DB_PATH

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Dual-engine configuration: PostgreSQL (preferred) → SQLite (fallback)
# ─────────────────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
USE_POSTGRES = DATABASE_URL.startswith("postgresql")

if USE_POSTGRES:
    try:
        import psycopg2
        import psycopg2.extras
        logger.info("PostgreSQL engine activated via DATABASE_URL")
    except ImportError:
        logger.warning(
            "DATABASE_URL is set but psycopg2 is not installed. "
            "Install with: pip install psycopg2-binary. Falling back to SQLite."
        )
        USE_POSTGRES = False


# ─────────────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS data_quarantine (
    quarantine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type   TEXT NOT NULL,
    record_json   TEXT NOT NULL,
    errors_json   TEXT NOT NULL,
    rejected_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
-- Static route and stop metadata
CREATE TABLE IF NOT EXISTS routes (
    route_id        TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    vehicle_type    TEXT NOT NULL,       -- 'bus' | 'train'
    color           TEXT NOT NULL,
    stops_json      TEXT NOT NULL,       -- JSON array of stop dicts
    headway_minutes INTEGER NOT NULL,
    first_departure TEXT NOT NULL,
    last_departure  TEXT NOT NULL,
    avg_speed_kmh   REAL NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Current state of every active vehicle (upserted each tick)
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id      TEXT PRIMARY KEY,
    route_id        TEXT NOT NULL,
    trip_id         TEXT,
    vehicle_type    TEXT NOT NULL,
    status          TEXT NOT NULL,       -- 'in_transit' | 'at_stop' | 'delayed' | 'completed'
    current_stop_id TEXT,
    next_stop_id    TEXT,
    lat             REAL,
    lon             REAL,
    speed_kmh       REAL,
    delay_seconds   REAL DEFAULT 0,
    occupancy       REAL DEFAULT 0,      -- 0.0 – 1.0 proxy
    heading         REAL,
    last_updated    TEXT NOT NULL,
    FOREIGN KEY (route_id) REFERENCES routes(route_id)
);

-- One record per trip (vehicle traversal of an entire route)
CREATE TABLE IF NOT EXISTS trips (
    trip_id              TEXT PRIMARY KEY,
    vehicle_id           TEXT NOT NULL,
    route_id             TEXT NOT NULL,
    scheduled_departure  TEXT NOT NULL,
    actual_departure     TEXT,
    scheduled_arrival    TEXT NOT NULL,
    actual_arrival       TEXT,
    delay_seconds        REAL DEFAULT 0,
    duration_seconds     REAL,
    stops_visited        INTEGER DEFAULT 0,
    total_stops          INTEGER NOT NULL,
    status               TEXT NOT NULL,  -- 'scheduled'|'in_progress'|'completed'|'cancelled'
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (route_id) REFERENCES routes(route_id)
);

-- High-frequency event stream (vehicle positions, stop arrivals/departures)
CREATE TABLE IF NOT EXISTS events (
    event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type      TEXT NOT NULL,   -- 'position_update'|'stop_arrival'|'stop_departure'|'delay'
    vehicle_id      TEXT NOT NULL,
    route_id        TEXT NOT NULL,
    trip_id         TEXT,
    stop_id         TEXT,
    lat             REAL,
    lon             REAL,
    delay_seconds   REAL DEFAULT 0,
    metadata_json   TEXT,            -- extra payload as JSON
    timestamp       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_events_timestamp   ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_route_id    ON events(route_id);
CREATE INDEX IF NOT EXISTS idx_events_vehicle_id  ON events(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_events_type        ON events(event_type);

-- Periodic KPI snapshots (written every ANALYTICS_SNAPSHOT_INTERVAL seconds)
CREATE TABLE IF NOT EXISTS analytics_snapshots (
    snapshot_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_time        TEXT NOT NULL DEFAULT (datetime('now')),
    total_vehicles       INTEGER,
    total_buses          INTEGER,
    total_trains         INTEGER,
    active_routes        INTEGER,
    avg_delay_seconds    REAL,
    max_delay_seconds    REAL,
    on_time_pct          REAL,         -- % of vehicles with delay < 60s
    trips_completed      INTEGER,
    trips_in_progress    INTEGER,
    peak_period          TEXT,         -- 'morning_peak'|'evening_peak'|'off_peak'
    metrics_json         TEXT          -- full per-route breakdown as JSON
);

-- Self-healing ETL execution log
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


# ─────────────────────────────────────────────────────────────────────────────
# Connection helper — Node C: Raw Data (PostgreSQL / SQLite)
# ─────────────────────────────────────────────────────────────────────────────

def get_engine_info() -> Dict[str, str]:
    """Return metadata about the active database engine (for dashboard display)."""
    if USE_POSTGRES:
        return {
            "engine": "PostgreSQL",
            "url": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL,
            "icon": "🐘",
        }
    return {
        "engine": "SQLite (WAL)",
        "url": str(DB_PATH),
        "icon": "🗄️",
    }


def get_pg_connection():
    """Return a psycopg2 connection to PostgreSQL."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn


def get_connection() -> sqlite3.Connection:
    """Return a thread-safe SQLite connection with WAL mode enabled.

    Note: When USE_POSTGRES is True, most bulk operations route through
    get_pg_connection(). This function always returns a SQLite connection
    for backward compatibility and local development.
    """
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(auto_migrate_legacy: bool = True) -> None:
    """Create all tables if they don't exist and safely migrate legacy data."""
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()

    engine = get_engine_info()
    logger.info("Database initialised — engine=%s at %s", engine["engine"], engine["url"])

    if auto_migrate_legacy and is_legacy_database():
        logger.warning(
            "Detected legacy Mumbai records in %s. Backing up and resetting database for Bengaluru simulation.",
            DB_PATH
        )
        reset_db(backup=True)


def backup_db(backup_path: Optional[str] = None) -> str:
    """Safely back up the SQLite database to a backup file."""
    src = Path(DB_PATH)
    if not src.exists():
        logger.info("Database file %s does not exist; skipping backup.", DB_PATH)
        return ""
    if not backup_path:
        backup_path = str(src.parent / "transit_mumbai_backup.db")

    Path(backup_path).parent.mkdir(parents=True, exist_ok=True)
    src_conn = sqlite3.connect(DB_PATH)
    dst_conn = sqlite3.connect(backup_path)
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    logger.info("Database backed up from %s to %s", DB_PATH, backup_path)
    return backup_path


def is_legacy_database() -> bool:
    """Check if the database contains old Mumbai simulation data."""
    if not Path(DB_PATH).exists():
        return False
    try:
        conn = get_connection()
        # Check routes table for Mumbai-specific route names
        row = conn.execute(
            "SELECT COUNT(*) FROM routes WHERE name LIKE '%CST%' OR name LIKE '%Bandra%' OR name LIKE '%Western Line%' OR name LIKE '%Navi Mumbai%'"
        ).fetchone()
        if row and row[0] > 0:
            conn.close()
            return True
        # Check events table for Mumbai latitudes (> 18.0)
        row_ev = conn.execute(
            "SELECT COUNT(*) FROM events WHERE lat > 18.0 LIMIT 1"
        ).fetchone()
        if row_ev and row_ev[0] > 0:
            conn.close()
            return True
        conn.close()
    except Exception as exc:
        logger.debug("Error checking legacy database: %s", exc)
    return False


def reset_db(backup: bool = True) -> None:
    """Safely back up and reset all tables in the database."""
    if backup:
        backup_db()
    conn = get_connection()
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("DELETE FROM events")
    conn.execute("DELETE FROM trips")
    conn.execute("DELETE FROM vehicles")
    conn.execute("DELETE FROM analytics_snapshots")
    conn.execute("DELETE FROM routes")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()
    from config import ROUTES
    upsert_routes(ROUTES)
    logger.info("Database %s successfully reset and populated with active Bengaluru routes.", DB_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

def upsert_routes(routes: List[Any]) -> None:
    """Insert (or replace) static route records from config Route objects."""
    conn = get_connection()
    for r in routes:
        stops_json = json.dumps([
            {"stop_id": s.stop_id, "name": s.name, "lat": s.lat, "lon": s.lon}
            for s in r.stops
        ])
        conn.execute("""
            INSERT OR REPLACE INTO routes
                (route_id, name, vehicle_type, color, stops_json,
                 headway_minutes, first_departure, last_departure, avg_speed_kmh)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (r.route_id, r.name, r.vehicle_type, r.color, stops_json,
              r.headway_minutes, r.first_departure, r.last_departure, r.avg_speed_kmh))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Vehicles
# ─────────────────────────────────────────────────────────────────────────────

def upsert_vehicle(v: Dict) -> None:
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO vehicles
            (vehicle_id, route_id, trip_id, vehicle_type, status,
             current_stop_id, next_stop_id, lat, lon, speed_kmh,
             delay_seconds, occupancy, heading, last_updated)
        VALUES (:vehicle_id,:route_id,:trip_id,:vehicle_type,:status,
                :current_stop_id,:next_stop_id,:lat,:lon,:speed_kmh,
                :delay_seconds,:occupancy,:heading,:last_updated)
    """, v)
    conn.commit()
    conn.close()


def upsert_vehicles_bulk(vehicles: List[Dict]) -> None:
    if not vehicles:
        return
    conn = get_connection()
    conn.executemany("""
        INSERT OR REPLACE INTO vehicles
            (vehicle_id, route_id, trip_id, vehicle_type, status,
             current_stop_id, next_stop_id, lat, lon, speed_kmh,
             delay_seconds, occupancy, heading, last_updated)
        VALUES (:vehicle_id,:route_id,:trip_id,:vehicle_type,:status,
                :current_stop_id,:next_stop_id,:lat,:lon,:speed_kmh,
                :delay_seconds,:occupancy,:heading,:last_updated)
    """, vehicles)
    conn.commit()
    conn.close()


def get_all_vehicles(active_only: bool = False) -> List[Dict]:
    conn = get_connection()
    if active_only:
        rows = conn.execute(
            "SELECT * FROM vehicles WHERE status IN ('in_transit', 'at_stop', 'delayed', 'scheduled')"
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM vehicles").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def complete_stale_vehicles() -> int:
    """Mark all active vehicles as completed (used at pipeline startup/cleanup)."""
    conn = get_connection()
    cur = conn.execute("UPDATE vehicles SET status = 'completed' WHERE status != 'completed'")
    count = cur.rowcount
    conn.commit()
    conn.close()
    return count


def get_vehicles_by_route(route_id: str) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM vehicles WHERE route_id = ?", (route_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Trips
# ─────────────────────────────────────────────────────────────────────────────

def upsert_trip(t: Dict) -> None:
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO trips
            (trip_id, vehicle_id, route_id, scheduled_departure, actual_departure,
             scheduled_arrival, actual_arrival, delay_seconds, duration_seconds,
             stops_visited, total_stops, status)
        VALUES (:trip_id,:vehicle_id,:route_id,:scheduled_departure,:actual_departure,
                :scheduled_arrival,:actual_arrival,:delay_seconds,:duration_seconds,
                :stops_visited,:total_stops,:status)
    """, t)
    conn.commit()
    conn.close()


def upsert_trips_bulk(trips: List[Dict]) -> None:
    if not trips:
        return
    conn = get_connection()
    conn.executemany("""
        INSERT OR REPLACE INTO trips
            (trip_id, vehicle_id, route_id, scheduled_departure, actual_departure,
             scheduled_arrival, actual_arrival, delay_seconds, duration_seconds,
             stops_visited, total_stops, status)
        VALUES (:trip_id,:vehicle_id,:route_id,:scheduled_departure,:actual_departure,
                :scheduled_arrival,:actual_arrival,:delay_seconds,:duration_seconds,
                :stops_visited,:total_stops,:status)
    """, trips)
    conn.commit()
    conn.close()


def get_active_trips() -> List[Dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM trips WHERE status = 'in_progress'"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_trips_by_route(route_id: str, limit: int = 100) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM trips WHERE route_id=? ORDER BY created_at DESC LIMIT ?",
        (route_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Events
# ─────────────────────────────────────────────────────────────────────────────

def insert_events_bulk(events: List[Dict]) -> None:
    if not events:
        return
    conn = get_connection()
    conn.executemany("""
        INSERT INTO events
            (event_type, vehicle_id, route_id, trip_id, stop_id,
             lat, lon, delay_seconds, metadata_json, timestamp)
        VALUES (:event_type,:vehicle_id,:route_id,:trip_id,:stop_id,
                :lat,:lon,:delay_seconds,:metadata_json,:timestamp)
    """, events)
    conn.commit()
    conn.close()


def get_recent_events(limit: int = 200, event_type: Optional[str] = None,
                      route_id: Optional[str] = None) -> List[Dict]:
    conn = get_connection()
    query = "SELECT * FROM events WHERE 1=1"
    params: List[Any] = []
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    if route_id:
        query += " AND route_id = ?"
        params.append(route_id)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stop_schedule(stop_id: str, limit: int = 20) -> List[Dict]:
    """Return recent arrivals/departures at a specific stop."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT e.*, r.name as route_name, r.vehicle_type, r.color
        FROM events e
        JOIN routes r ON e.route_id = r.route_id
        WHERE e.stop_id = ?
          AND e.event_type IN ('stop_arrival','stop_departure')
        ORDER BY e.timestamp DESC
        LIMIT ?
    """, (stop_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Analytics Snapshots
# ─────────────────────────────────────────────────────────────────────────────

def insert_snapshot(snap: Dict) -> None:
    conn = get_connection()
    conn.execute("""
        INSERT INTO analytics_snapshots
            (snapshot_time, total_vehicles, total_buses, total_trains,
             active_routes, avg_delay_seconds, max_delay_seconds,
             on_time_pct, trips_completed, trips_in_progress,
             peak_period, metrics_json)
        VALUES (:snapshot_time,:total_vehicles,:total_buses,:total_trains,
                :active_routes,:avg_delay_seconds,:max_delay_seconds,
                :on_time_pct,:trips_completed,:trips_in_progress,
                :peak_period,:metrics_json)
    """, snap)
    conn.commit()
    conn.close()


def get_snapshots(limit: int = 100) -> List[Dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM analytics_snapshots ORDER BY snapshot_time DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_route_list() -> List[Dict]:
    conn = get_connection()
    rows = conn.execute("SELECT route_id, name, vehicle_type, color, stops_json FROM routes").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_etl_run_logs(limit: int = 50) -> List[Dict]:
    """Retrieve recent ETL run execution records."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM etl_run_log ORDER BY started_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_quarantine_records(limit: int = 50) -> List[Dict]:
    """Retrieve recent data quarantine records."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM data_quarantine ORDER BY rejected_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Transit Database Utilities")
    parser.add_argument("--backup", action="store_true", help="Create a backup of the current database")
    parser.add_argument("--reset", action="store_true", help="Back up and reset database for Bengaluru simulation")
    parser.add_argument("--status", action="store_true", help="Show current row counts and check for legacy data")
    args = parser.parse_args()

    if args.backup:
        out = backup_db()
        print(f"Database backed up to: {out}")
    elif args.reset:
        reset_db(backup=True)
        print("Database successfully reset and seeded with Bengaluru routes.")
    elif args.status:
        init_db(auto_migrate_legacy=False)
        conn = get_connection()
        print(f"Database Path: {DB_PATH}")
        print(f"Legacy Mumbai Data Detected: {is_legacy_database()}")
        for tbl in ["routes", "vehicles", "trips", "events", "analytics_snapshots", "data_quarantine", "etl_run_log"]:
            cnt = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            print(f"  {tbl:<22}: {cnt} rows")
        conn.close()
    else:
        init_db()

