"""
analytics.py — SQL-backed analytics queries for the transit pipeline.

All functions return pandas DataFrames ready for direct use in Streamlit charts.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import numpy as np

import database as db

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _conn():
    return db.get_connection()


def _df(rows: List[Dict]) -> pd.DataFrame:
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Live Vehicle Overview
# ─────────────────────────────────────────────────────────────────────────────

def get_live_vehicles() -> pd.DataFrame:
    """All currently active vehicles with route metadata."""
    conn = _conn()
    df = pd.read_sql_query("""
        SELECT v.*,
               r.name        AS route_name,
               r.color       AS route_color,
               r.stops_json  AS stops_json
        FROM vehicles v
        JOIN routes r ON v.route_id = r.route_id
        WHERE v.status NOT IN ('completed','cancelled')
    """, conn)
    conn.close()
    return df


def get_vehicle_count_by_type() -> pd.DataFrame:
    """Count of active vehicles split by bus / train."""
    conn = _conn()
    df = pd.read_sql_query("""
        SELECT vehicle_type, COUNT(*) AS count
        FROM vehicles
        WHERE status NOT IN ('completed','cancelled')
        GROUP BY vehicle_type
    """, conn)
    conn.close()
    return df


def get_vehicle_count_by_route() -> pd.DataFrame:
    """Active vehicle count per route, with route metadata."""
    conn = _conn()
    df = pd.read_sql_query("""
        SELECT v.route_id, r.name AS route_name, r.vehicle_type,
               r.color, COUNT(*) AS vehicle_count,
               AVG(v.delay_seconds) AS avg_delay,
               AVG(v.occupancy)     AS avg_occupancy
        FROM vehicles v
        JOIN routes r ON v.route_id = r.route_id
        WHERE v.status NOT IN ('completed','cancelled')
        GROUP BY v.route_id
        ORDER BY vehicle_count DESC
    """, conn)
    conn.close()
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. Delays
# ─────────────────────────────────────────────────────────────────────────────

def get_delay_distribution(vehicle_type: Optional[str] = None) -> pd.DataFrame:
    """Delay values for all active vehicles (for histogram)."""
    conn = _conn()
    q = """
        SELECT v.vehicle_id, v.route_id, r.name AS route_name,
               r.vehicle_type, v.delay_seconds, v.status
        FROM vehicles v
        JOIN routes r ON v.route_id = r.route_id
        WHERE v.status NOT IN ('completed','cancelled')
    """
    params = []
    if vehicle_type:
        q += " AND r.vehicle_type = ?"
        params.append(vehicle_type)
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    return df


def get_route_avg_delay() -> pd.DataFrame:
    """Average delay per route from recent events (last 1 hour of sim time)."""
    conn = _conn()
    cutoff = (datetime.now() - timedelta(hours=2)).isoformat()
    df = pd.read_sql_query("""
        SELECT e.route_id, r.name AS route_name, r.vehicle_type, r.color,
               AVG(e.delay_seconds) AS avg_delay,
               MAX(e.delay_seconds) AS max_delay,
               COUNT(*)             AS event_count
        FROM events e
        JOIN routes r ON e.route_id = r.route_id
        WHERE e.timestamp > ?
          AND e.event_type = 'position_update'
        GROUP BY e.route_id
        ORDER BY avg_delay DESC
    """, conn, params=(cutoff,))
    conn.close()
    return df


def get_delay_over_time(route_id: Optional[str] = None,
                         limit: int = 200) -> pd.DataFrame:
    """Delay trend over time (for line chart)."""
    conn = _conn()
    q = """
        SELECT e.timestamp, e.route_id, r.name AS route_name,
               e.delay_seconds
        FROM events e
        JOIN routes r ON e.route_id = r.route_id
        WHERE e.event_type = 'position_update'
    """
    params = []
    if route_id:
        q += " AND e.route_id = ?"
        params.append(route_id)
    q += " ORDER BY e.timestamp DESC LIMIT ?"
    params.append(limit)
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 3. Arrival / Departure Times
# ─────────────────────────────────────────────────────────────────────────────

def get_stop_events(stop_id: Optional[str] = None,
                    event_types: Optional[List[str]] = None,
                    limit: int = 100) -> pd.DataFrame:
    """Recent stop arrival / departure events."""
    conn = _conn()
    q = """
        SELECT e.*, r.name AS route_name, r.vehicle_type, r.color
        FROM events e
        JOIN routes r ON e.route_id = r.route_id
        WHERE e.event_type IN ('stop_arrival','stop_departure')
    """
    params: List = []
    if stop_id:
        q += " AND e.stop_id = ?"
        params.append(stop_id)
    if event_types:
        placeholders = ",".join("?" * len(event_types))
        q += f" AND e.event_type IN ({placeholders})"
        params.extend(event_types)
    q += " ORDER BY e.timestamp DESC LIMIT ?"
    params.append(limit)
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def get_all_stops() -> List[Dict]:
    """All unique stops across all routes."""
    from config import STOP_BY_ID
    return [{"stop_id": sid, "name": s.name, "lat": s.lat, "lon": s.lon}
            for sid, s in STOP_BY_ID.items()]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Trip Duration
# ─────────────────────────────────────────────────────────────────────────────

def get_trip_durations(route_id: Optional[str] = None,
                        status: str = "completed",
                        limit: int = 300) -> pd.DataFrame:
    """Completed trip durations for distribution analysis."""
    conn = _conn()
    q = """
        SELECT t.*, r.name AS route_name, r.vehicle_type, r.color
        FROM trips t
        JOIN routes r ON t.route_id = r.route_id
        WHERE t.status = ?
          AND t.duration_seconds IS NOT NULL
    """
    params: List = [status]
    if route_id:
        q += " AND t.route_id = ?"
        params.append(route_id)
    q += " ORDER BY t.created_at DESC LIMIT ?"
    params.append(limit)
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    return df


def get_trip_summary() -> pd.DataFrame:
    """Summary counts of trips by status and route."""
    conn = _conn()
    df = pd.read_sql_query("""
        SELECT t.route_id, r.name AS route_name, r.vehicle_type,
               t.status, COUNT(*) AS count,
               AVG(t.delay_seconds)    AS avg_delay,
               AVG(t.duration_seconds) AS avg_duration
        FROM trips t
        JOIN routes r ON t.route_id = r.route_id
        GROUP BY t.route_id, t.status
        ORDER BY t.route_id, t.status
    """, conn)
    conn.close()
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 5. Peak Travel Periods
# ─────────────────────────────────────────────────────────────────────────────

def get_peak_heatmap() -> pd.DataFrame:
    """
    Returns hour-of-day × day-of-week vehicle count matrix from snapshots.
    Used to render the peak period heatmap.
    """
    conn = _conn()
    df = pd.read_sql_query("""
        SELECT snapshot_time, total_vehicles, peak_period
        FROM analytics_snapshots
        ORDER BY snapshot_time
    """, conn)
    conn.close()

    if df.empty:
        return df

    df["snapshot_time"] = pd.to_datetime(df["snapshot_time"])
    df["hour"]     = df["snapshot_time"].dt.hour
    df["day_name"] = df["snapshot_time"].dt.strftime("%A")
    df["day_num"]  = df["snapshot_time"].dt.dayofweek

    pivot = df.groupby(["day_name", "hour"])["total_vehicles"].mean().reset_index()
    pivot.columns = ["day", "hour", "avg_vehicles"]
    return pivot


def get_hourly_delay_profile() -> pd.DataFrame:
    """Average delay by hour of day across all events."""
    conn = _conn()
    df = pd.read_sql_query("""
        SELECT strftime('%H', timestamp) AS hour_str,
               AVG(delay_seconds) AS avg_delay,
               COUNT(*) AS event_count
        FROM events
        WHERE event_type = 'position_update'
        GROUP BY hour_str
        ORDER BY hour_str
    """, conn)
    conn.close()
    if not df.empty:
        df["hour"] = df["hour_str"].astype(int)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 6. Route Performance Leaderboard
# ─────────────────────────────────────────────────────────────────────────────

def get_route_performance_leaderboard() -> pd.DataFrame:
    """
    Build a leaderboard from the latest analytics snapshot metrics_json.
    Falls back to live vehicle data if no snapshots yet.
    """
    conn = _conn()
    row = conn.execute(
        "SELECT metrics_json FROM analytics_snapshots ORDER BY snapshot_time DESC LIMIT 1"
    ).fetchone()
    conn.close()

    if row and row["metrics_json"]:
        data = json.loads(row["metrics_json"])
        df = pd.DataFrame(list(data.values()))
        if not df.empty:
            df = df.sort_values("perf_score", ascending=False).reset_index(drop=True)
            df.index += 1
        return df

    # Fallback: compute from live vehicles
    vehicles = db.get_all_vehicles()
    if not vehicles:
        return pd.DataFrame()
    from processor import compute_route_performance
    perf = compute_route_performance(vehicles)
    df = pd.DataFrame(list(perf.values()))
    if not df.empty:
        df = df.sort_values("perf_score", ascending=False).reset_index(drop=True)
        df.index += 1
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 7. Historical KPI Trend
# ─────────────────────────────────────────────────────────────────────────────

def get_kpi_trend(limit: int = 200) -> pd.DataFrame:
    """KPI values over time from analytics_snapshots table."""
    conn = _conn()
    df = pd.read_sql_query("""
        SELECT snapshot_time, total_vehicles, avg_delay_seconds,
               on_time_pct, trips_completed, trips_in_progress, peak_period
        FROM analytics_snapshots
        ORDER BY snapshot_time DESC
        LIMIT ?
    """, conn, params=(limit,))
    conn.close()
    if not df.empty:
        df["snapshot_time"] = pd.to_datetime(df["snapshot_time"])
        df = df.sort_values("snapshot_time")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 8. Overall Summary KPIs  (for dashboard header cards)
# ─────────────────────────────────────────────────────────────────────────────

def get_summary_kpis() -> Dict:
    """Fast summary numbers for the top KPI cards."""
    conn = _conn()

    # Latest snapshot
    snap = conn.execute(
        "SELECT * FROM analytics_snapshots ORDER BY snapshot_time DESC LIMIT 1"
    ).fetchone()

    # Live counts
    live = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN vehicle_type='bus'   THEN 1 ELSE 0 END) AS buses,
            SUM(CASE WHEN vehicle_type='metro' THEN 1 ELSE 0 END) AS trains,
            AVG(delay_seconds) AS avg_delay,
            SUM(CASE WHEN delay_seconds < 60 THEN 1 ELSE 0 END) * 100.0 / MAX(COUNT(*),1) AS on_time_pct,
            COUNT(DISTINCT route_id) AS active_routes
        FROM vehicles
        WHERE status NOT IN ('completed','cancelled')
    """).fetchone()

    trips_done = conn.execute(
        "SELECT COUNT(*) FROM trips WHERE status='completed'"
    ).fetchone()[0]

    conn.close()

    if snap:
        peak = snap["peak_period"]
    else:
        from processor import get_peak_period
        peak = get_peak_period(datetime.now())

    from processor import get_peak_label
    return {
        "total_vehicles": live["total"] or 0,
        "buses":          live["buses"] or 0,
        "trains":         live["trains"] or 0,
        "active_routes":  live["active_routes"] or 0,
        "avg_delay_s":    round(live["avg_delay"] or 0, 1),
        "on_time_pct":    round(live["on_time_pct"] or 0, 1),
        "trips_completed": trips_done or 0,
        "peak_period":    peak,
        "peak_label":     get_peak_label(peak),
    }
