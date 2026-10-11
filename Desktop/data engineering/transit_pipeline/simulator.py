"""
simulator.py — High-fidelity GTFS-style public transport simulator.

Simulates vehicle movement along configured routes, generating:
  - Vehicle position updates (lat/lon interpolated along polyline)
  - Realistic delays (log-normal distribution, peak-sensitive)
  - Stop arrival / departure events
  - Trip lifecycle (scheduled → in_progress → completed)
  - Occupancy load proxy (higher at peak hours)
"""

import math
import json
import random
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np

from config import (
    ROUTES, ROUTE_BY_ID,
    PEAK_HOURS,
    DELAY_PROBABILITY_NORMAL, DELAY_PROBABILITY_PEAK,
    DELAY_MEAN_SECONDS, DELAY_STD_SECONDS,
    SIMULATION_TICK_SECONDS,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Geo Helpers
# ─────────────────────────────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance between two points in kilometres."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def interpolate_position(lat1: float, lon1: float,
                          lat2: float, lon2: float,
                          fraction: float) -> Tuple[float, float]:
    """Linear interpolation between two coordinates."""
    fraction = max(0.0, min(1.0, fraction))
    return lat1 + (lat2 - lat1) * fraction, lon1 + (lon2 - lon1) * fraction


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compass bearing (0-360) from point 1 to point 2."""
    dlon = math.radians(lon2 - lon1)
    lat1r, lat2r = math.radians(lat1), math.radians(lat2)
    x = math.sin(dlon) * math.cos(lat2r)
    y = math.cos(lat1r) * math.sin(lat2r) - math.sin(lat1r) * math.cos(lat2r) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


# ─────────────────────────────────────────────────────────────────────────────
# Delay / Occupancy Generation
# ─────────────────────────────────────────────────────────────────────────────

def is_peak_hour(dt: datetime) -> bool:
    h = dt.hour
    for (start, end) in PEAK_HOURS.values():
        if start <= h < end:
            return True
    return False


def peak_period_label(dt: datetime) -> str:
    h = dt.hour
    if PEAK_HOURS["morning"][0] <= h < PEAK_HOURS["morning"][1]:
        return "morning_peak"
    if PEAK_HOURS["evening"][0] <= h < PEAK_HOURS["evening"][1]:
        return "evening_peak"
    return "off_peak"


def sample_delay(is_peak: bool) -> float:
    """Sample a delay in seconds from a log-normal distribution."""
    prob = DELAY_PROBABILITY_PEAK if is_peak else DELAY_PROBABILITY_NORMAL
    if random.random() > prob:
        return 0.0
    # Log-normal: mean and std in normal-space
    sigma = math.sqrt(math.log(1 + (DELAY_STD_SECONDS / DELAY_MEAN_SECONDS) ** 2))
    mu    = math.log(DELAY_MEAN_SECONDS) - sigma ** 2 / 2
    return float(np.random.lognormal(mu, sigma))


def sample_occupancy(is_peak: bool, stop_fraction: float) -> float:
    """Proxy for passenger load: peaks mid-route and during rush hours."""
    base = 0.65 if is_peak else 0.30
    curve = math.sin(math.pi * stop_fraction)   # bell curve over route
    noise = random.uniform(-0.05, 0.05)
    return max(0.0, min(1.0, base * curve + noise + base * 0.2))


# ─────────────────────────────────────────────────────────────────────────────
# Vehicle State
# ─────────────────────────────────────────────────────────────────────────────

class VehicleState:
    """Tracks a single vehicle through its route lifecycle."""

    def __init__(self, vehicle_id: str, route_id: str, trip_id: str,
                 scheduled_departure: datetime, dwell_time_seconds: int = 30):
        self.vehicle_id           = vehicle_id
        self.route_id             = route_id
        self.trip_id              = trip_id
        self.route                = ROUTE_BY_ID[route_id]
        self.stops                = self.route.stops
        self.n_stops              = len(self.stops)

        self.current_stop_idx     = 0          # index in self.stops
        self.segment_progress     = 0.0        # 0.0 → 1.0 between stops
        self.dwell_remaining      = 0.0        # seconds remaining at stop

        self.scheduled_departure  = scheduled_departure
        self.actual_departure: Optional[datetime] = None
        self.scheduled_arrival    = self._compute_scheduled_arrival()
        self.actual_arrival: Optional[datetime]   = None

        self.delay_seconds        = 0.0
        self.total_delay_added    = 0.0
        self.stops_visited        = 0
        self.status               = "scheduled"  # scheduled|in_progress|at_stop|delayed|completed

        self.lat                  = self.stops[0].lat
        self.lon                  = self.stops[0].lon
        self.speed_kmh            = 0.0
        self.heading              = 0.0
        self.occupancy            = 0.0
        self.dwell_time_s         = dwell_time_seconds

        # Pre-compute inter-stop distances
        self.segment_distances: List[float] = []
        for i in range(self.n_stops - 1):
            d = haversine(self.stops[i].lat, self.stops[i].lon,
                          self.stops[i+1].lat, self.stops[i+1].lon)
            self.segment_distances.append(max(d, 0.001))  # avoid zero-div

    def _compute_scheduled_arrival(self) -> datetime:
        total_km = sum(
            haversine(self.stops[i].lat, self.stops[i].lon,
                      self.stops[i+1].lat, self.stops[i+1].lon)
            for i in range(len(self.stops) - 1)
        )
        hours = total_km / self.route.avg_speed_kmh
        return self.scheduled_departure + timedelta(hours=hours)

    def is_completed(self) -> bool:
        return self.status == "completed"

    def tick(self, dt_seconds: float, now: datetime) -> List[Dict]:
        """Advance simulation by dt_seconds. Returns list of events emitted."""
        if self.status in ("completed", "cancelled"):
            return []

        events: List[Dict] = []
        peak = is_peak_hour(now)

        # ── Scheduled → in_progress ─────────────────────────────────────────
        if self.status == "scheduled":
            if now >= self.scheduled_departure:
                delay = sample_delay(peak)
                self.delay_seconds    = delay
                self.total_delay_added = delay
                self.actual_departure = self.scheduled_departure + timedelta(seconds=delay)
                self.status           = "at_stop"
                self.dwell_remaining  = self.dwell_time_s
                self.stops_visited    = 1
                events.append(self._make_event("stop_arrival", self.stops[0].stop_id, now))
        
        # ── Dwell at stop ────────────────────────────────────────────────────
        elif self.status == "at_stop":
            self.dwell_remaining -= dt_seconds
            self.speed_kmh = 0.0
            if self.dwell_remaining <= 0:
                # Depart stop
                events.append(self._make_event("stop_departure", self.stops[self.current_stop_idx].stop_id, now))
                self.current_stop_idx += 1
                if self.current_stop_idx >= self.n_stops:
                    self._complete(now, events)
                else:
                    self.segment_progress = 0.0
                    self.status = "in_transit"

        # ── Moving between stops ─────────────────────────────────────────────
        elif self.status in ("in_transit", "delayed"):
            seg_dist_km = self.segment_distances[self.current_stop_idx - 1]
            
            # Occasionally inject new delay mid-segment
            if random.random() < 0.02:  # 2% chance per tick
                extra = sample_delay(peak)
                self.delay_seconds    += extra
                self.total_delay_added += extra

            # Speed with noise
            speed_noise = random.uniform(0.7, 1.15)
            eff_speed   = self.route.avg_speed_kmh * speed_noise
            if self.delay_seconds > 0:
                eff_speed *= random.uniform(0.5, 0.85)  # slow when delayed
            self.speed_kmh = eff_speed

            # Advance along segment
            km_per_tick          = eff_speed * (dt_seconds / 3600.0)
            progress_delta       = km_per_tick / seg_dist_km
            self.segment_progress = min(1.0, self.segment_progress + progress_delta)

            # Update position
            prev_stop = self.stops[self.current_stop_idx - 1]
            next_stop = self.stops[self.current_stop_idx]
            self.lat, self.lon = interpolate_position(
                prev_stop.lat, prev_stop.lon,
                next_stop.lat, next_stop.lon,
                self.segment_progress,
            )
            self.heading  = bearing(prev_stop.lat, prev_stop.lon, next_stop.lat, next_stop.lon)
            stop_fraction = (self.current_stop_idx - 1 + self.segment_progress) / max(self.n_stops - 1, 1)
            self.occupancy = sample_occupancy(peak, stop_fraction)

            self.status = "delayed" if self.delay_seconds > 60 else "in_transit"

            # Emit position update every tick
            events.append(self._make_event("position_update", None, now))

            # Arrived at next stop
            if self.segment_progress >= 1.0:
                self.lat, self.lon = next_stop.lat, next_stop.lon
                self.stops_visited += 1
                self.status        = "at_stop"
                self.dwell_remaining = self.dwell_time_s + random.uniform(-5, 15)
                if self.delay_seconds > 0:
                    self.delay_seconds = max(0, self.delay_seconds - random.uniform(10, 45))
                events.append(self._make_event("stop_arrival", next_stop.stop_id, now))

        return events

    def _complete(self, now: datetime, events: List[Dict]) -> None:
        self.status         = "completed"
        self.actual_arrival = now
        self.lat            = self.stops[-1].lat
        self.lon            = self.stops[-1].lon
        self.speed_kmh      = 0.0
        events.append(self._make_event("stop_arrival", self.stops[-1].stop_id, now))

    def _make_event(self, event_type: str, stop_id: Optional[str], now: datetime) -> Dict:
        return {
            "event_type":    event_type,
            "vehicle_id":    self.vehicle_id,
            "route_id":      self.route_id,
            "trip_id":       self.trip_id,
            "stop_id":       stop_id,
            "lat":           round(self.lat, 6),
            "lon":           round(self.lon, 6),
            "delay_seconds": round(self.delay_seconds, 1),
            "metadata_json": json.dumps({
                "speed_kmh": round(self.speed_kmh, 1),
                "occupancy": round(self.occupancy, 3),
                "heading":   round(self.heading, 1),
                "stop_idx":  self.current_stop_idx,
            }),
            "timestamp":     now.isoformat(timespec="seconds"),
        }

    def to_vehicle_dict(self, now: datetime) -> Dict:
        return {
            "vehicle_id":       self.vehicle_id,
            "route_id":         self.route_id,
            "bus_number":       getattr(self.route, "bus_number", self.route_id),
            "bus_name":         getattr(self.route, "display_name", self.route.name),
            "destination_sign": getattr(self.route, "destination_sign", self.stops[-1].name),
            "trip_id":          self.trip_id,
            "vehicle_type":     self.route.vehicle_type,
            "status":           self.status,
            "current_stop_id":  self.stops[min(self.current_stop_idx, self.n_stops - 1)].stop_id,
            "next_stop_id":     (self.stops[self.current_stop_idx].stop_id
                                 if self.current_stop_idx < self.n_stops else None),
            "lat":              round(self.lat, 6),
            "lon":              round(self.lon, 6),
            "speed_kmh":        round(self.speed_kmh, 1),
            "delay_seconds":    round(self.delay_seconds, 1),
            "occupancy":        round(self.occupancy, 3),
            "heading":          round(self.heading, 1),
            "last_updated":     now.isoformat(timespec="seconds"),
        }

    def to_trip_dict(self) -> Dict:
        duration = None
        if self.actual_departure and self.actual_arrival:
            duration = (self.actual_arrival - self.actual_departure).total_seconds()
        return {
            "trip_id":             self.trip_id,
            "vehicle_id":          self.vehicle_id,
            "route_id":            self.route_id,
            "scheduled_departure": self.scheduled_departure.isoformat(timespec="seconds"),
            "actual_departure":    (self.actual_departure.isoformat(timespec="seconds")
                                    if self.actual_departure else None),
            "scheduled_arrival":   self.scheduled_arrival.isoformat(timespec="seconds"),
            "actual_arrival":      (self.actual_arrival.isoformat(timespec="seconds")
                                    if self.actual_arrival else None),
            "delay_seconds":       round(self.total_delay_added, 1),
            "duration_seconds":    round(duration, 1) if duration else None,
            "stops_visited":       self.stops_visited,
            "total_stops":         self.n_stops,
            "status":              ("completed" if self.status == "completed"
                                    else "scheduled" if self.status == "scheduled"
                                    else "in_progress"),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Simulator (Fleet Manager)
# ─────────────────────────────────────────────────────────────────────────────

def generate_vehicle_display_id(route_id: str, k: int) -> str:
    """Generate realistic Karnataka BMTC registration number or Namma Metro train ID."""
    if "Metro" in route_id:
        if "L1" in route_id:
            return f"BMRCL Train #T-1{k+1:02d}"
        elif "L2" in route_id:
            return f"BMRCL Train #T-2{k+1:02d}"
        else:
            return f"BMRCL Train #T-3{k+1:02d}"

    bus_prefixes = {
        "BUS-101": ("KA-01-F", 4500),   # Volvo Vajra (Whitefield)
        "BUS-102": ("KA-57-F", 1880),   # Hosur/Electronic City
        "BUS-103": ("KA-04-G", 3310),   # Ring Road Circular
        "BUS-104": ("KA-01-FA", 1100),  # Koramangala Loop
        "BUS-105": ("KA-57-F", 2240),   # Vayu Vajra Airport
        "BUS-106": ("KA-53-F", 6700),   # IT Corridor Feeder
    }
    pfx, base_num = bus_prefixes.get(route_id, ("KA-01-F", 1000))
    return f"{pfx}-{base_num + (k + 1) * 7}"


class TransitSimulator:
    """
    Manages the entire simulated fleet across all routes.

    Usage:
        sim = TransitSimulator()
        tick_result = sim.tick()
        # tick_result has: vehicles, trips, events
    """

    def __init__(self, time_acceleration: float = 60.0):
        """
        Args:
            time_acceleration: How many simulated seconds pass per real second.
                60 = 1 simulated minute per real second (default, comfortable demo speed).
                1  = real-time (very slow for a demo).
        """
        self.time_acceleration = time_acceleration
        self._vehicles: Dict[str, VehicleState] = {}
        self._completed_trips: List[Dict]        = []
        # Synchronized to real-world current local time
        self._sim_time: datetime                 = datetime.now().replace(microsecond=0)
        self._initialise_fleet()
        logger.info("Simulator initialised. %d active vehicles.", len(self._vehicles))

    # ── Fleet initialisation ─────────────────────────────────────────────────

    def _initialise_fleet(self) -> None:
        """Seed the fleet with vehicles already in-progress at sim start time."""
        for route in ROUTES:
            self._spawn_vehicles_for_route(route, initial=True)

    def _spawn_vehicles_for_route(self, route, initial: bool = False) -> None:
        """Create vehicles spaced by headway across the route."""
        headway_sec = route.headway_minutes * 60
        # How many vehicles fit on route simultaneously?
        total_km = sum(
            haversine(route.stops[i].lat, route.stops[i].lon,
                      route.stops[i+1].lat, route.stops[i+1].lon)
            for i in range(len(route.stops) - 1)
        )
        route_duration_sec = (total_km / route.avg_speed_kmh) * 3600
        n_simultaneous = max(1, int(route_duration_sec / headway_sec) + 1)

        for k in range(n_simultaneous):
            dep_time = self._sim_time - timedelta(seconds=k * headway_sec)
            vehicle_id = generate_vehicle_display_id(route.route_id, k)
            trip_id    = f"{route.route_id}-T{dep_time.strftime('%H%M')}-{k+1:02d}"

            vs = VehicleState(vehicle_id, route.route_id, trip_id, dep_time)
            if initial:
                # Fast-forward to current sim time
                elapsed = (self._sim_time - dep_time).total_seconds()
                if elapsed > 0:
                    self._fast_forward(vs, elapsed)
            self._vehicles[vehicle_id] = vs

    def _fast_forward(self, vs: VehicleState, seconds: float) -> None:
        """Advance a vehicle state without recording events."""
        step = 30.0  # coarse steps for init
        t = vs.scheduled_departure
        remaining = seconds
        while remaining > 0 and not vs.is_completed():
            s = min(step, remaining)
            vs.tick(s, t)
            t += timedelta(seconds=s)
            remaining -= s

    # ── Main tick ────────────────────────────────────────────────────────────

    def tick(self) -> Dict:
        """
        Advance simulation by SIMULATION_TICK_SECONDS × time_acceleration.
        Returns dict with 'vehicles', 'trips', 'events', 'sim_time'.
        """
        dt = SIMULATION_TICK_SECONDS * self.time_acceleration
        self._sim_time += timedelta(seconds=dt)
        now = self._sim_time

        all_events:   List[Dict] = []
        all_vehicles: List[Dict] = []
        all_trips:    List[Dict] = []

        completed_ids: List[str] = []

        for vid, vs in list(self._vehicles.items()):
            events = vs.tick(dt, now)
            all_events.extend(events)
            all_vehicles.append(vs.to_vehicle_dict(now))
            all_trips.append(vs.to_trip_dict())

            if vs.is_completed():
                self._completed_trips.append(vs.to_trip_dict())
                completed_ids.append(vid)

        # Remove completed vehicles, spawn replacements
        for vid in completed_ids:
            route_id = self._vehicles[vid].route_id
            del self._vehicles[vid]
            self._respawn(route_id, now)

        return {
            "sim_time":  now,
            "vehicles":  all_vehicles,
            "trips":     all_trips,
            "events":    all_events,
        }

    def _respawn(self, route_id: str, now: datetime) -> None:
        """Launch a new vehicle for a route after the previous one completes."""
        route      = ROUTE_BY_ID[route_id]
        # Count existing vehicles on this route
        existing   = [v for v in self._vehicles.values() if v.route_id == route_id]
        k          = len(existing)
        vehicle_id = generate_vehicle_display_id(route_id, k)
        trip_id    = f"{route_id}-T{now.strftime('%H%M%S')}"
        vs         = VehicleState(vehicle_id, route_id, trip_id, now)
        self._vehicles[vehicle_id] = vs

    @property
    def sim_time(self) -> datetime:
        return self._sim_time

    def get_active_vehicles(self) -> List[Dict]:
        """Return dict representations of all currently active vehicles in the simulator."""
        now = self._sim_time
        return [
            v.to_vehicle_dict(now)
            for v in self._vehicles.values()
            if not v.is_completed()
        ]

    def get_fleet_summary(self) -> Dict:
        now = self._sim_time
        vehicles = list(self._vehicles.values())
        total = len(vehicles)
        buses  = sum(1 for v in vehicles if v.route.vehicle_type == "bus")
        trains = sum(1 for v in vehicles if v.route.vehicle_type == "metro")
        delays = [v.delay_seconds for v in vehicles]
        avg_delay = float(np.mean(delays)) if delays else 0.0
        max_delay = float(np.max(delays))  if delays else 0.0
        on_time   = sum(1 for d in delays if d < 60) / max(total, 1) * 100
        return {
            "sim_time":      now.strftime("%Y-%m-%d %H:%M:%S"),
            "total_vehicles": total,
            "buses":          buses,
            "trains":         trains,
            "avg_delay_s":    round(avg_delay, 1),
            "max_delay_s":    round(max_delay, 1),
            "on_time_pct":    round(on_time, 1),
            "peak_period":    peak_period_label(now),
        }
