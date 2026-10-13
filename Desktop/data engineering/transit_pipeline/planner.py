"""
planner.py — Multi-Modal Journey Planner for Bengaluru Transit Pipeline.

Provides smart routing between any origin and destination in Bengaluru:
  1. Direct Bus and Metro options
  2. Multi-modal transfer routes (Metro ↔ Bus, Metro ↔ Metro) with walking interchanges
  3. Real-world ETAs based on vehicle speeds, stop dwell times, headways, and live delays
  4. Cost/Fare estimation and carbon savings
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import config
from config import ROUTES, ROUTE_BY_ID, STOP_BY_ID, Route, Stop
from simulator import haversine
import database as db
import processor as proc


@dataclass
class JourneyLeg:
    route_id: str
    route_name: str
    vehicle_type: str           # "bus" | "metro"
    color: str
    board_stop: Stop
    alight_stop: Stop
    intermediate_stops: List[Stop]
    num_stops: int
    distance_km: float
    in_vehicle_minutes: float
    wait_minutes: float
    headway_minutes: int
    live_delay_minutes: float
    path_coords: List[Tuple[float, float]]  # [(lat, lon), ...]
    board_time: datetime = field(default_factory=datetime.now)      # Arrival of vehicle at board_stop
    alight_time: datetime = field(default_factory=datetime.now)     # Arrival of vehicle at alight_stop
    vehicle_id: str = "Scheduled"
    proximity: str = "⏳ Scheduled"
    is_live: bool = False
    bus_name: str = ""          # e.g. "BMTC Volvo Vajra 335-E"
    bus_number: str = ""        # e.g. "335-E"
    destination_sign: str = ""  # e.g. "ITPL / Whitefield (via Marathahalli)"


@dataclass
class JourneyPlan:
    plan_id: str
    plan_type: str              # "direct" | "transfer"
    badge: str
    recommended: bool
    legs: List[JourneyLeg]
    transfer_stops: List[Tuple[Stop, Stop, float]]  # (alight_stop, next_board_stop, walk_minutes)
    total_duration_minutes: float
    total_distance_km: float
    total_stops: int
    transfer_count: int
    fare_inr: int
    departure_time: datetime
    arrival_time: datetime
    co2_saved_kg: float
    summary: str
    walk_to_first_stop_minutes: float = 0.0
    walk_to_first_stop_meters: float = 0.0
    user_location_name: str = ""
    user_coords: Optional[Tuple[float, float]] = None


# Popular Bengaluru localities / user current location hubs
BENGALURU_LOCALITIES: Dict[str, Tuple[float, float]] = {
    "Koramangala (Sony World / 5th Block)": (12.9352, 77.6245),
    "Indiranagar (100ft Road / CMH Road)": (12.9784, 77.6408),
    "HSR Layout (Sector 1 / BDA Complex)": (12.9116, 77.6389),
    "Whitefield (ITPL Main Gate)": (12.9856, 77.7314),
    "Electronic City (Phase 1 Wipro Gate)": (12.8452, 77.6602),
    "MG Road / Brigade Road (Central)": (12.9738, 77.6085),
    "Kempegowda Bus Station (Majestic)": (12.9772, 77.5713),
    "Jayanagar (4th Block Complex)": (12.9308, 77.5838),
    "Malleshwaram (8th Cross Margosa)": (12.9982, 77.5704),
    "Hebbal (Flyover / Esteem Mall)": (13.0358, 77.5970),
    "Marathahalli (Bridge / Multiplex)": (12.9553, 77.7011),
    "Bellandur (EcoSpace Tech Park)": (12.9257, 77.6844),
    "Banashankari (Bus Station TTMC)": (12.9156, 77.5736),
    "Silk Board (Central Junction)": (12.9172, 77.6228),
    "Yelahanka (NES Signal / Police Station)": (13.1007, 77.5963),
    "BTM Layout (Udupi Garden)": (12.9166, 77.6101),
    "Domlur (Flyover / EGL)": (12.9609, 77.6387),
}


def find_nearest_stops(lat: float, lon: float, top_k: int = 3) -> List[Tuple[Stop, float, float]]:
    """
    Find the closest transit stops to given coordinates.
    Returns list of (Stop, distance_meters, walk_minutes).
    """
    all_unique_stops: Dict[str, Stop] = {}
    for r in ROUTES:
        for s in r.stops:
            if s.name not in all_unique_stops:
                all_unique_stops[s.name] = s

    stops_with_dist = []
    for s in all_unique_stops.values():
        dist_km = haversine(lat, lon, s.lat, s.lon)
        dist_m = round(dist_km * 1000.0)
        # Walking speed ~4.5 km/h = 75 m/min
        walk_mins = max(1.0, round(dist_m / 75.0, 1))
        stops_with_dist.append((s, dist_m, walk_mins))

    stops_with_dist.sort(key=lambda x: x[1])
    return stops_with_dist[:top_k]


def find_nearby_transit_stops(lat: float, lon: float, top_k: int = 5) -> List[Dict[str, any]]:
    """
    Find nearby transit stops to given coordinates with detailed metadata
    including geodesic distance in meters, walk duration in minutes,
    connected routes, and transit modes.
    """
    places = get_all_places()
    results = []
    for p in places:
        dist_km = haversine(lat, lon, p["lat"], p["lon"])
        dist_m = round(dist_km * 1000.0)
        walk_mins = max(1.0, round(dist_m / 75.0, 1))
        results.append({
            "name": p["name"],
            "lat": p["lat"],
            "lon": p["lon"],
            "distance_meters": dist_m,
            "walk_minutes": walk_mins,
            "routes": sorted(list(p["routes"])),
            "modes": sorted(list(p["modes"])),
        })
    results.sort(key=lambda x: x["distance_meters"])
    return results[:top_k]


def find_nearest_bus_stations(lat: float, lon: float, top_k: int = 10) -> List[Dict[str, any]]:
    """
    Find nearest bus stations/stops to given coordinates with detailed distance,
    walk duration, bus numbers, and route details.
    The first element is the closest bus station.
    """
    bus_stops_map: Dict[str, Dict[str, any]] = {}
    for r in ROUTES:
        if r.vehicle_type == "bus":
            for s in r.stops:
                if s.name not in bus_stops_map:
                    bus_stops_map[s.name] = {
                        "name": s.name,
                        "stop_id": s.stop_id,
                        "lat": s.lat,
                        "lon": s.lon,
                        "routes": [],
                        "route_names": [],
                        "bus_numbers": [],
                    }
                if r.route_id not in bus_stops_map[s.name]["routes"]:
                    bus_stops_map[s.name]["routes"].append(r.route_id)
                    bus_stops_map[s.name]["route_names"].append(r.display_name or r.name)
                    bus_num = r.bus_number or r.route_id
                    if bus_num not in bus_stops_map[s.name]["bus_numbers"]:
                        bus_stops_map[s.name]["bus_numbers"].append(bus_num)

    results = []
    for s_name, data in bus_stops_map.items():
        dist_km = haversine(lat, lon, data["lat"], data["lon"])
        dist_m = round(dist_km * 1000.0)
        walk_mins = max(1.0, round(dist_m / 75.0, 1))
        results.append({
            "name": data["name"],
            "stop_id": data["stop_id"],
            "lat": data["lat"],
            "lon": data["lon"],
            "distance_meters": dist_m,
            "distance_km": round(dist_km, 2),
            "walk_minutes": walk_mins,
            "routes": sorted(list(data["routes"])),
            "route_names": data["route_names"],
            "bus_numbers": sorted(list(data["bus_numbers"])),
        })

    results.sort(key=lambda x: x["distance_meters"])
    return results[:top_k]


def get_all_places() -> List[Dict[str, any]]:
    """
    Return all unique transit locations in Bengaluru with metadata
    (stop_id, name, lat, lon, connected routes and transit modes).
    """
    places_map: Dict[str, Dict[str, any]] = {}
    for r in ROUTES:
        for s in r.stops:
            if s.name not in places_map:
                places_map[s.name] = {
                    "name": s.name,
                    "lat": s.lat,
                    "lon": s.lon,
                    "stops": [],
                    "routes": [],
                    "modes": set(),
                }
            places_map[s.name]["stops"].append(s.stop_id)
            if r.route_id not in places_map[s.name]["routes"]:
                places_map[s.name]["routes"].append(r.route_id)
            places_map[s.name]["modes"].add(r.vehicle_type)

    places = list(places_map.values())
    places.sort(key=lambda p: p["name"])
    return places


def get_stop_by_name(name: str) -> Optional[Stop]:
    """Find a Stop object by its name."""
    for r in ROUTES:
        for s in r.stops:
            if s.name.lower() == name.lower():
                return s
    return None


def _calculate_live_delay_for_route(route_id: str) -> float:
    """Retrieve the current live average delay in minutes for this route from database."""
    try:
        conn = db.get_connection()
        row = conn.execute(
            "SELECT AVG(delay_seconds) FROM vehicles WHERE route_id=?", (route_id,)
        ).fetchone()
        conn.close()
        if row and row[0] is not None:
            return max(0.0, float(row[0]) / 60.0)
    except Exception:
        pass
    return 0.0


def _build_leg(
    route: Route,
    start_idx: int,
    end_idx: int,
    base_time: datetime,
    vehicles: Optional[List[Dict]] = None,
) -> JourneyLeg:
    """Build a single leg of travel along a route with live/scheduled arrival timing."""
    if start_idx <= end_idx:
        leg_stops = route.stops[start_idx : end_idx + 1]
    else:
        stop_idx = None if end_idx == 0 else end_idx - 1
        leg_stops = route.stops[start_idx : stop_idx : -1]

    if not leg_stops:
        # Fallback safeguard
        leg_stops = [route.stops[start_idx], route.stops[end_idx]]

    total_dist = 0.0
    coords = []
    for i in range(len(leg_stops)):
        coords.append((leg_stops[i].lat, leg_stops[i].lon))
        if i > 0:
            total_dist += haversine(
                leg_stops[i - 1].lat, leg_stops[i - 1].lon,
                leg_stops[i].lat, leg_stops[i].lon
            )

    # In-vehicle travel time: distance / speed + 40s dwell per stop
    dwell_mins = max(0, len(leg_stops) - 1) * 0.65
    travel_mins = (total_dist / route.avg_speed_kmh) * 60.0 + dwell_mins

    # Real-time arrival at boarding stop
    arr_info = None
    if vehicles:
        arr_info = proc.get_next_arrival_for_route(leg_stops[0].stop_id, route.route_id, vehicles, base_time)

    if arr_info:
        wait_seconds = max(0, arr_info["eta_seconds"])
        wait_mins = round(wait_seconds / 60.0, 1)
        board_time = base_time + timedelta(seconds=wait_seconds)
        vehicle_id = proc.format_vehicle_number(arr_info["vehicle_id"], route.route_id)
        proximity = arr_info["proximity"]
        is_live = arr_info["is_live"]
        live_delay_mins = round(arr_info.get("delay_s", 0.0) / 60.0, 1)
    else:
        # Timetable headway fallback
        wait_seconds = int((route.headway_minutes * 60) / 2.0)
        wait_mins = round(route.headway_minutes / 2.0, 1)
        board_time = base_time + timedelta(seconds=wait_seconds)
        b_num_str = getattr(route, "bus_number", route.route_id)
        vehicle_id = f"Scheduled ({b_num_str})"
        proximity = f"⏳ Scheduled (Every {route.headway_minutes}m)"
        is_live = False
        live_delay_mins = round(_calculate_live_delay_for_route(route.route_id), 1)

    alight_time = board_time + timedelta(minutes=travel_mins + live_delay_mins)

    return JourneyLeg(
        route_id=route.route_id,
        route_name=route.name,
        vehicle_type=route.vehicle_type,
        color=route.color,
        board_stop=leg_stops[0],
        alight_stop=leg_stops[-1],
        intermediate_stops=leg_stops[1:-1],
        num_stops=len(leg_stops) - 1,
        distance_km=round(total_dist, 2),
        in_vehicle_minutes=round(travel_mins, 1),
        wait_minutes=wait_mins,
        headway_minutes=route.headway_minutes,
        live_delay_minutes=live_delay_mins,
        path_coords=coords,
        board_time=board_time,
        alight_time=alight_time,
        vehicle_id=vehicle_id,
        proximity=proximity,
        is_live=is_live,
        bus_name=getattr(route, "display_name", route.name),
        bus_number=getattr(route, "bus_number", route.route_id),
        destination_sign=getattr(route, "destination_sign", leg_stops[-1].name),
    )


def _estimate_fare(legs: List[JourneyLeg]) -> int:
    """Estimate total fare in INR based on BMTC bus and Namma Metro fare slabs."""
    total_fare = 0
    for leg in legs:
        d = leg.distance_km
        if leg.vehicle_type == "metro":
            # Namma Metro fare: 0-2km: ₹10, 2-5km: ₹20, 5-10km: ₹30, 10-15km: ₹40, >15km: ₹50-60
            if d <= 2.5:
                fare = 10
            elif d <= 5.0:
                fare = 20
            elif d <= 10.0:
                fare = 30
            elif d <= 16.0:
                fare = 45
            else:
                fare = 60
        else:
            # BMTC Bus: 0-3km: ₹10, 3-7km: ₹15, 7-12km: ₹20, 12-20km: ₹25, airport express ₹150+
            if "Airport" in leg.route_name or "KIA" in leg.route_name:
                fare = 250
            elif d <= 3.0:
                fare = 10
            elif d <= 7.0:
                fare = 15
            elif d <= 12.0:
                fare = 22
            elif d <= 20.0:
                fare = 28
            else:
                fare = 35
        total_fare += fare
    return total_fare


def _estimate_carbon_saved_kg(distance_km: float) -> float:
    """Estimated CO2 saved compared to a private single-occupancy petrol car (~130g/km)."""
    return round(distance_km * 0.125, 2)


def find_journeys(
    origin_name: str,
    dest_name: str,
    departure_time: Optional[datetime] = None,
    max_options: int = 5,
    vehicles: Optional[List[Dict]] = None,
    user_coords: Optional[Tuple[float, float]] = None,
) -> List[JourneyPlan]:
    """
    Search and find the best routes between origin and destination.
    Supports user current GPS location or Bengaluru localities.
    Guarantees at least 3 distinct ranked options.
    """
    if origin_name.strip().lower() == dest_name.strip().lower():
        return []

    if departure_time is None:
        departure_time = datetime.now()

    if vehicles is None:
        try:
            vehicles = db.get_all_vehicles(active_only=True)
        except Exception:
            vehicles = []

    plans: List[JourneyPlan] = []

    # Check if origin is a user current location (GPS coordinates or Bengaluru locality)
    walk_to_stop_m = 0.0
    walk_to_stop_mins = 0.0
    u_loc_name = ""
    active_user_coords = None

    if user_coords:
        active_user_coords = user_coords
        u_loc_name = origin_name or "My Current Location"
    elif origin_name in BENGALURU_LOCALITIES:
        active_user_coords = BENGALURU_LOCALITIES[origin_name]
        u_loc_name = origin_name

    effective_origin_name = origin_name
    departure_time_transit = departure_time

    if active_user_coords:
        # Check if origin_name is already a specific transit stop selected by the commuter
        chosen_stop = get_stop_by_name(origin_name)
        if chosen_stop:
            dist_km = haversine(active_user_coords[0], active_user_coords[1], chosen_stop.lat, chosen_stop.lon)
            walk_to_stop_m = round(dist_km * 1000.0)
            walk_to_stop_mins = max(1.0, round(walk_to_stop_m / 75.0, 1))
            effective_origin_name = chosen_stop.name
            departure_time_transit = departure_time + timedelta(minutes=walk_to_stop_mins)
        else:
            nearest = find_nearest_stops(active_user_coords[0], active_user_coords[1], top_k=2)
            if nearest:
                closest_stop, dist_m, w_mins = nearest[0]
                effective_origin_name = closest_stop.name
                walk_to_stop_m = dist_m
                walk_to_stop_mins = w_mins
                departure_time_transit = departure_time + timedelta(minutes=walk_to_stop_mins)

    # Map all stops matching origin_name and dest_name
    origin_stops = [s for r in ROUTES for s in r.stops if s.name.lower() == effective_origin_name.lower()]
    dest_stops = [s for r in ROUTES for s in r.stops if s.name.lower() == dest_name.lower()]

    if not origin_stops:
        origin_ref = get_stop_by_name(effective_origin_name)
    else:
        origin_ref = origin_stops[0]

    if not dest_stops:
        dest_ref = get_stop_by_name(dest_name)
    else:
        dest_ref = dest_stops[0]

    if not origin_ref or not dest_ref:
        return []

    # ─────────────────────────────────────────────────────────────────────────
    # 1. DIRECT ROUTES
    # ─────────────────────────────────────────────────────────────────────────
    direct_candidates = []
    for r in ROUTES:
        o_indices = [i for i, s in enumerate(r.stops) if s.name.lower() == effective_origin_name.lower() or haversine(s.lat, s.lon, origin_ref.lat, origin_ref.lon) < 0.6]
        d_indices = [i for i, s in enumerate(r.stops) if s.name.lower() == dest_name.lower() or haversine(s.lat, s.lon, dest_ref.lat, dest_ref.lon) < 0.6]

        for oi in o_indices:
            for di in d_indices:
                if oi != di:
                    leg = _build_leg(r, oi, di, departure_time_transit, vehicles=vehicles)
                    direct_candidates.append(leg)

    for leg in direct_candidates:
        total_mins = round((leg.alight_time - departure_time).total_seconds() / 60.0, 1)
        arr_time = leg.alight_time
        badge = "🚇 Direct Metro" if leg.vehicle_type == "metro" else "🚌 Direct Bus"

        plan = JourneyPlan(
            plan_id=f"direct_{leg.route_id}_{leg.board_stop.stop_id}_{leg.alight_stop.stop_id}",
            plan_type="direct",
            badge=badge,
            recommended=False,
            legs=[leg],
            transfer_stops=[],
            total_duration_minutes=total_mins,
            total_distance_km=leg.distance_km,
            total_stops=leg.num_stops,
            transfer_count=0,
            fare_inr=_estimate_fare([leg]),
            departure_time=departure_time,
            arrival_time=arr_time,
            co2_saved_kg=_estimate_carbon_saved_kg(leg.distance_km),
            summary=f"Direct {leg.vehicle_type.upper()} via {leg.route_name} ({leg.num_stops} stops, {total_mins:.0f} mins)",
            walk_to_first_stop_minutes=walk_to_stop_mins,
            walk_to_first_stop_meters=walk_to_stop_m,
            user_location_name=u_loc_name,
            user_coords=active_user_coords,
        )
        plans.append(plan)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. 1-TRANSFER MULTI-MODAL ROUTES
    # ─────────────────────────────────────────────────────────────────────────
    transfer_candidates = []
    for r1 in ROUTES:
        r1_o_indices = [i for i, s in enumerate(r1.stops) if s.name.lower() == effective_origin_name.lower() or haversine(s.lat, s.lon, origin_ref.lat, origin_ref.lon) < 0.6]
        if not r1_o_indices:
            continue

        for r2 in ROUTES:
            if r1.route_id == r2.route_id:
                continue

            r2_d_indices = [i for i, s in enumerate(r2.stops) if s.name.lower() == dest_name.lower() or haversine(s.lat, s.lon, dest_ref.lat, dest_ref.lon) < 0.6]
            if not r2_d_indices:
                continue

            # Look for transfer stops between r1 and r2
            for i1, s1 in enumerate(r1.stops):
                for i2, s2 in enumerate(r2.stops):
                    walk_dist = haversine(s1.lat, s1.lon, s2.lat, s2.lon)
                    if s1.name.lower() == s2.name.lower() or walk_dist < 0.6:
                        walk_mins = round(3.0 + (walk_dist / 4.0) * 60.0, 1)

                        for oi in r1_o_indices:
                            for di in r2_d_indices:
                                if oi != i1 and di != i2:
                                    leg1 = _build_leg(r1, oi, i1, departure_time_transit, vehicles=vehicles)
                                    leg2_ready = leg1.alight_time + timedelta(minutes=walk_mins)
                                    leg2 = _build_leg(r2, i2, di, leg2_ready, vehicles=vehicles)

                                    direct_crow_dist = haversine(origin_ref.lat, origin_ref.lon, dest_ref.lat, dest_ref.lon)
                                    if (leg1.distance_km + leg2.distance_km) > max(45.0, direct_crow_dist * 4.0):
                                        continue

                                    transfer_candidates.append((leg1, leg2, s1, s2, walk_mins))

    # Deduplicate and format transfer candidates
    seen_transfers = set()
    for leg1, leg2, s1, s2, walk_mins in transfer_candidates:
        sig = f"{leg1.route_id}_{s1.name}_{leg2.route_id}_{s2.name}"
        if sig in seen_transfers:
            continue
        seen_transfers.add(sig)

        total_mins = round((leg2.alight_time - departure_time).total_seconds() / 60.0, 1)
        total_dist = round(leg1.distance_km + leg2.distance_km, 2)
        arr_time = leg2.alight_time

        mode_badge = f"{'🚇' if leg1.vehicle_type == 'metro' else '🚌'} + {'🚇' if leg2.vehicle_type == 'metro' else '🚌'} Transfer"

        plan = JourneyPlan(
            plan_id=f"xfer_{sig}",
            plan_type="transfer",
            badge=mode_badge,
            recommended=False,
            legs=[leg1, leg2],
            transfer_stops=[(s1, s2, walk_mins)],
            total_duration_minutes=total_mins,
            total_distance_km=total_dist,
            total_stops=leg1.num_stops + leg2.num_stops,
            transfer_count=1,
            fare_inr=_estimate_fare([leg1, leg2]),
            departure_time=departure_time,
            arrival_time=arr_time,
            co2_saved_kg=_estimate_carbon_saved_kg(total_dist),
            summary=f"{leg1.vehicle_type.upper()} ({leg1.route_name}) ➔ Interchange at {s1.name} ➔ {leg2.vehicle_type.upper()} ({leg2.route_name})",
            walk_to_first_stop_minutes=walk_to_stop_mins,
            walk_to_first_stop_meters=walk_to_stop_m,
            user_location_name=u_loc_name,
            user_coords=active_user_coords,
        )
        plans.append(plan)

    if not plans:
        return []

    # ─────────────────────────────────────────────────────────────────────────
    # Ensure at least 3 distinct options are always available
    # ─────────────────────────────────────────────────────────────────────────
    if 0 < len(plans) < 3:
        num_needed = 3 - len(plans)
        seed_plans = list(plans)
        for k in range(num_needed):
            base_plan = seed_plans[k % len(seed_plans)]
            first_leg = base_plan.legs[0]
            hw = max(8, first_leg.headway_minutes) * (k + 1)
            next_dep = base_plan.departure_time + timedelta(minutes=hw)

            # Build legs for this subsequent departure
            next_legs = []
            cur_t = next_dep + timedelta(minutes=base_plan.walk_to_first_stop_minutes)
            for idx, leg in enumerate(base_plan.legs):
                route_obj = ROUTE_BY_ID.get(leg.route_id)
                if route_obj:
                    try:
                        s_i = next(i for i, s in enumerate(route_obj.stops) if s.stop_id == leg.board_stop.stop_id)
                        e_i = next(i for i, s in enumerate(route_obj.stops) if s.stop_id == leg.alight_stop.stop_id)
                        n_leg = _build_leg(route_obj, s_i, e_i, cur_t, vehicles=vehicles)
                        next_legs.append(n_leg)
                        if idx < len(base_plan.transfer_stops):
                            cur_t = n_leg.alight_time + timedelta(minutes=base_plan.transfer_stops[idx][2])
                    except StopIteration:
                        next_legs.append(leg)
                else:
                    next_legs.append(leg)

            next_arr = next_legs[-1].alight_time
            total_m = round((next_arr - next_dep).total_seconds() / 60.0, 1)

            next_plan = JourneyPlan(
                plan_id=f"next_{base_plan.plan_id}_{k+1}",
                plan_type=base_plan.plan_type,
                badge=f"🕒 Next Service (+{hw}m)",
                recommended=False,
                legs=next_legs,
                transfer_stops=list(base_plan.transfer_stops),
                total_duration_minutes=total_m,
                total_distance_km=base_plan.total_distance_km,
                total_stops=base_plan.total_stops,
                transfer_count=base_plan.transfer_count,
                fare_inr=base_plan.fare_inr,
                departure_time=next_dep,
                arrival_time=next_arr,
                co2_saved_kg=base_plan.co2_saved_kg,
                summary=f"Next {first_leg.vehicle_type.upper()} ({first_leg.route_name}) • Departs in +{hw}m",
                walk_to_first_stop_minutes=base_plan.walk_to_first_stop_minutes,
                walk_to_first_stop_meters=base_plan.walk_to_first_stop_meters,
                user_location_name=base_plan.user_location_name,
                user_coords=base_plan.user_coords,
            )
            plans.append(next_plan)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. RANKING & RECOMMENDATION (Sorted by least time to reach destination)
    # ─────────────────────────────────────────────────────────────────────────
    plans.sort(key=lambda p: (p.total_duration_minutes, p.transfer_count))

    # Mark the fastest/best route as recommended
    if plans:
        plans[0].recommended = True
        plans[0].badge = f"⚡ Fastest ({plans[0].badge})"

    return plans[:max(3, max_options)]
