"""
processor.py — Processes raw simulator output into enriched analytics.

Responsibilities:
  • Classify delay severity
  • Compute route-level performance scores
  • Detect current peak period
  • Build per-route KPI summaries for snapshot storage
  • Produce a departure board for any given stop
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
import logging

import numpy as np

from config import ROUTE_BY_ID, PEAK_HOURS, ROUTES

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Delay Classification
# ─────────────────────────────────────────────────────────────────────────────

DELAY_BANDS = [
    (0,    60,   "on_time",    "🟢"),
    (60,   300,  "minor",      "🟡"),
    (300,  600,  "moderate",   "🟠"),
    (600,  1800, "severe",     "🔴"),
    (1800, 9e9,  "critical",   "⚫"),
]


def classify_delay(delay_seconds: float) -> Tuple[str, str]:
    """Return (category, emoji) for a delay value."""
    for lo, hi, cat, emoji in DELAY_BANDS:
        if lo <= delay_seconds < hi:
            return cat, emoji
    return "critical", "⚫"


def format_delay(delay_seconds: float) -> str:
    """Human-readable delay string, e.g. '3m 20s late' or 'On time'."""
    if delay_seconds < 60:
        return "On time"
    mins = int(delay_seconds) // 60
    secs = int(delay_seconds) % 60
    return f"{mins}m {secs:02d}s late"


# ─────────────────────────────────────────────────────────────────────────────
# Peak Period Detection
# ─────────────────────────────────────────────────────────────────────────────

def get_peak_period(dt: datetime) -> str:
    h = dt.hour
    if PEAK_HOURS["morning"][0] <= h < PEAK_HOURS["morning"][1]:
        return "morning_peak"
    if PEAK_HOURS["evening"][0] <= h < PEAK_HOURS["evening"][1]:
        return "evening_peak"
    return "off_peak"


def get_peak_label(period: str) -> str:
    return {
        "morning_peak": "🌅 Morning Peak",
        "evening_peak": "🌆 Evening Peak",
        "off_peak":     "🌙 Off-Peak",
    }.get(period, period)


# ─────────────────────────────────────────────────────────────────────────────
# Route Performance Scoring
# ─────────────────────────────────────────────────────────────────────────────

def compute_route_performance(vehicles: List[Dict]) -> Dict[str, Dict]:
    """
    Aggregate vehicle states into per-route performance metrics.
    
    Args:
        vehicles: List of vehicle dicts from latest tick.
    
    Returns:
        Dict keyed by route_id with performance metrics.
    """
    # Group by route
    route_groups: Dict[str, List[Dict]] = {}
    for v in vehicles:
        rid = v["route_id"]
        route_groups.setdefault(rid, []).append(v)

    perf: Dict[str, Dict] = {}

    for rid, vlist in route_groups.items():
        route = ROUTE_BY_ID.get(rid)
        if not route:
            continue

        delays        = [v["delay_seconds"] for v in vlist]
        speeds        = [v["speed_kmh"] for v in vlist if v["speed_kmh"] > 0]
        occupancies   = [v["occupancy"] for v in vlist]
        n             = len(vlist)

        avg_delay     = float(np.mean(delays))  if delays      else 0.0
        max_delay     = float(np.max(delays))   if delays      else 0.0
        avg_speed     = float(np.mean(speeds))  if speeds      else 0.0
        avg_occupancy = float(np.mean(occupancies)) if occupancies else 0.0
        on_time_pct   = sum(1 for d in delays if d < 60) / max(n, 1) * 100

        # Performance score 0-100: penalise delays, reward on-time rate
        score = max(0.0, min(100.0,
            on_time_pct * 0.6
            + (1 - avg_delay / max(avg_delay + 300, 300)) * 40
        ))

        delay_cat, _ = classify_delay(avg_delay)

        perf[rid] = {
            "route_id":      rid,
            "route_name":    route.name,
            "vehicle_type":  route.vehicle_type,
            "color":         route.color,
            "vehicle_count": n,
            "avg_delay_s":   round(avg_delay, 1),
            "max_delay_s":   round(max_delay, 1),
            "avg_speed_kmh": round(avg_speed, 1),
            "avg_occupancy": round(avg_occupancy, 3),
            "on_time_pct":   round(on_time_pct, 1),
            "perf_score":    round(score, 1),
            "delay_band":    delay_cat,
            "delay_label":   format_delay(avg_delay),
        }

    return perf


# ─────────────────────────────────────────────────────────────────────────────
# Snapshot Builder
# ─────────────────────────────────────────────────────────────────────────────

def build_snapshot(vehicles: List[Dict], trips: List[Dict],
                   sim_time: datetime) -> Dict:
    """
    Build an analytics_snapshots record from current vehicle + trip state.
    """
    delays  = [v["delay_seconds"] for v in vehicles]
    n_total = len(vehicles)
    n_buses  = sum(1 for v in vehicles if v["vehicle_type"] == "bus")
    n_trains = sum(1 for v in vehicles if v["vehicle_type"] == "metro")

    active_routes = len({v["route_id"] for v in vehicles})
    avg_delay = float(np.mean(delays)) if delays else 0.0
    max_delay = float(np.max(delays))  if delays else 0.0
    on_time   = sum(1 for d in delays if d < 60) / max(n_total, 1) * 100

    trips_completed   = sum(1 for t in trips if t["status"] == "completed")
    trips_in_progress = sum(1 for t in trips if t["status"] == "in_progress")

    route_perf = compute_route_performance(vehicles)

    return {
        "snapshot_time":      sim_time.isoformat(timespec="seconds"),
        "total_vehicles":     n_total,
        "total_buses":        n_buses,
        "total_trains":       n_trains,
        "active_routes":      active_routes,
        "avg_delay_seconds":  round(avg_delay, 1),
        "max_delay_seconds":  round(max_delay, 1),
        "on_time_pct":        round(on_time, 1),
        "trips_completed":    trips_completed,
        "trips_in_progress":  trips_in_progress,
        "peak_period":        get_peak_period(sim_time),
        "metrics_json":       json.dumps(route_perf),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Departure Board Generator
# ─────────────────────────────────────────────────────────────────────────────

def format_vehicle_number(vid: str, route_id: str) -> str:
    """Format or map vehicle ID to a clean Karnataka transport fleet registration or train number."""
    if not vid:
        return vid
    if vid.startswith("KA-") or vid.startswith("BMRCL"):
        return vid
    if vid.startswith("BUS-") or vid.startswith("Metro-"):
        from simulator import generate_vehicle_display_id
        try:
            k = int(vid.split("V")[1].split("-")[0]) - 1
        except Exception:
            k = 0
        return generate_vehicle_display_id(route_id, max(0, k))
    return vid


def build_departure_board(stop_id: str, vehicles: List[Dict], sim_time: datetime,
                          max_entries: int = 15) -> List[Dict]:
    """
    Generate an accurate real-time departure/arrival board for a stop.
    Includes:
      1. Vehicles currently boarding at this stop
      2. Vehicles approaching from upstream stops (1, 2, 3+ stops away)
      3. Upcoming scheduled departures based on route headways
    """
    from simulator import haversine
    from datetime import timedelta

    board = []
    # Routes that serve this stop
    routes = [r for r in ROUTES if any(s.stop_id == stop_id for s in r.stops)]

    # Filter active vehicles (ignore completed)
    active_vehicles = [v for v in vehicles if v.get("status") != "completed"]

    for route in routes:
        stop_indices = [i for i, s in enumerate(route.stops) if s.stop_id == stop_id]
        if not stop_indices:
            continue
        target_idx = stop_indices[0]
        target_stop = route.stops[target_idx]
        dest_stop = route.stops[-1]

        route_vehicles = [v for v in active_vehicles if v.get("route_id") == route.route_id]
        found_active_count = 0

        for v in route_vehicles:
            c_sid = v.get("current_stop_id")
            c_indices = [i for i, s in enumerate(route.stops) if s.stop_id == c_sid]
            c_idx = c_indices[0] if c_indices else 0

            # If vehicle has passed target stop, skip
            if c_idx > target_idx:
                continue

            delay_s = float(v.get("delay_seconds") or 0.0)
            delay_cat, delay_emoji = classify_delay(delay_s)

            if c_idx == target_idx and v.get("status") == "at_stop":
                eta_sec = 0.0
                proximity = "🟢 Boarding Now"
            else:
                stops_away = max(1, target_idx - c_idx)
                if v.get("lat") and v.get("lon"):
                    dist_km = haversine(v["lat"], v["lon"], target_stop.lat, target_stop.lon)
                else:
                    dist_km = sum(
                        haversine(route.stops[j].lat, route.stops[j].lon,
                                  route.stops[j+1].lat, route.stops[j+1].lon)
                        for j in range(c_idx, target_idx)
                    ) if c_idx < target_idx else 0.5

                speed = max(float(v.get("speed_kmh") or 0.0), route.avg_speed_kmh * 0.75, 8.0)
                dwell_sec = max(0, stops_away - 1) * 35.0
                travel_sec = (dist_km / speed) * 3600.0 + dwell_sec + delay_s
                eta_sec = max(30.0, travel_sec)

                # Current location hint
                curr_stop_name = route.stops[c_idx].name if c_idx < len(route.stops) else ""
                if stops_away == 1:
                    proximity = "📍 1 stop away"
                elif curr_stop_name:
                    proximity = f"📍 {stops_away} stops away ({curr_stop_name})"
                else:
                    proximity = f"📍 {stops_away} stops away"

            eta_time = sim_time + timedelta(seconds=round(eta_sec))
            eta_mins = round(eta_sec) // 60
            eta_rem_s = round(eta_sec) % 60
            eta_str = "Now" if eta_sec < 45 else (f"{eta_mins}m {eta_rem_s:02d}s" if eta_mins > 0 else f"{eta_rem_s}s")

            veh_id_formatted = format_vehicle_number(v.get("vehicle_id", ""), route.route_id)

            board.append({
                "route_id":         route.route_id,
                "route_name":       route.name,
                "bus_name":         getattr(route, "display_name", route.name),
                "bus_number":       getattr(route, "bus_number", route.route_id),
                "destination_sign": getattr(route, "destination_sign", dest_stop.name),
                "vehicle_type":     route.vehicle_type,
                "vehicle_id":       veh_id_formatted,
                "destination":      dest_stop.name,
                "eta_seconds":      round(eta_sec),
                "eta_time":         eta_time.strftime("%I:%M %p"),
                "eta_str":          eta_str,
                "proximity":        proximity,
                "delay_s":          delay_s,
                "delay_label":      format_delay(delay_s),
                "delay_emoji":      delay_emoji,
                "delay_band":       delay_cat,
                "color":            route.color,
                "is_live":          True,
            })
            found_active_count += 1

        # Add upcoming scheduled dispatches so timetable is never blank
        headway_sec = route.headway_minutes * 60
        base_wait = 180 if found_active_count == 0 else headway_sec
        # Ensure at least 2 future departures are listed for each line
        target_future = max(2, 3 - found_active_count)
        for rep in range(target_future):
            sch_eta_sec = base_wait + (rep * headway_sec)
            sch_eta_time = sim_time + timedelta(seconds=sch_eta_sec)
            sch_mins = sch_eta_sec // 60

            board.append({
                "route_id":         route.route_id,
                "route_name":       route.name,
                "bus_name":         getattr(route, "display_name", route.name),
                "bus_number":       getattr(route, "bus_number", route.route_id),
                "destination_sign": getattr(route, "destination_sign", dest_stop.name),
                "vehicle_type":     route.vehicle_type,
                "vehicle_id":       f"Scheduled ({getattr(route, 'bus_number', route.route_id)})",
                "destination":      dest_stop.name,
                "eta_seconds":      sch_eta_sec,
                "eta_time":         sch_eta_time.strftime("%I:%M %p"),
                "eta_str":          f"in {sch_mins}m",
                "proximity":        f"⏳ Scheduled Dispatch (Every {route.headway_minutes}m)",
                "delay_s":          0.0,
                "delay_label":      "Scheduled",
                "delay_emoji":      "🗓️",
                "delay_band":       "on_time",
                "color":            route.color,
                "is_live":          False,
            })

    board.sort(key=lambda x: x["eta_seconds"])
    return board[:max_entries]


def get_next_arrival_for_route(stop_id: str, route_id: str, vehicles: List[Dict],
                               sim_time: datetime) -> Optional[Dict]:
    """Retrieve the next approaching or scheduled vehicle for a specific route at a stop."""
    board = build_departure_board(stop_id, vehicles, sim_time, max_entries=25)
    for entry in board:
        if entry["route_id"] == route_id:
            return entry
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Trip Duration Categorisation
# ─────────────────────────────────────────────────────────────────────────────

DURATION_BANDS = [
    (0,    600,   "< 10 min"),
    (600,  1800,  "10–30 min"),
    (1800, 3600,  "30–60 min"),
    (3600, 7200,  "1–2 hrs"),
    (7200, 9e9,   "> 2 hrs"),
]


def categorise_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "Unknown"
    for lo, hi, label in DURATION_BANDS:
        if lo <= seconds < hi:
            return label
    return "> 2 hrs"
