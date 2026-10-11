# quality.py
import json
import math
from config import ROUTES

# Routes and stops known to this simulation
VALID_ROUTE_IDS = {route.route_id for route in ROUTES}

VALID_STOP_IDS = {
    stop.stop_id
    for route in ROUTES
    for stop in route.stops
}

# Broad Bengaluru simulation bounds
LAT_MIN, LAT_MAX = 12.70, 13.35
LON_MIN, LON_MAX = 77.35, 77.85


def is_missing(value):
    return value is None or (
        isinstance(value, str) and not value.strip()
    )


def is_finite_number(value):
    if isinstance(value, bool) or is_missing(value):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def validate_record(record, record_type):
    """Return a list of validation errors for one record."""
    errors = []

    type_map = {
        "vehicle": "vehicles", "vehicles": "vehicles",
        "event": "events",     "events": "events",
        "trip": "trips",       "trips": "trips",
    }
    norm_type = type_map.get(record_type, record_type)

    required = {
        "vehicles": [
            "vehicle_id", "route_id", "vehicle_type",
            "lat", "lon", "delay_seconds",
        ],
        "events": [
            "event_type", "vehicle_id", "route_id",
            "timestamp",
        ],
        "trips": [
            "trip_id", "vehicle_id", "route_id", "status",
        ],
    }

    if norm_type not in required:
        return [f"unknown_record_type_{record_type}"]

    for field in required[norm_type]:
        if is_missing(record.get(field)):
            errors.append(f"missing_{field}")

    route_id = record.get("route_id")
    if not is_missing(route_id) and route_id not in VALID_ROUTE_IDS:
        errors.append("invalid_route_id")

    if norm_type == "vehicles":
        lat = record.get("lat")
        lon = record.get("lon")
        delay = record.get("delay_seconds")

        if not is_finite_number(lat):
            errors.append("invalid_latitude")
        elif not LAT_MIN <= float(lat) <= LAT_MAX:
            errors.append("latitude_out_of_bounds")

        if not is_finite_number(lon):
            errors.append("invalid_longitude")
        elif not LON_MIN <= float(lon) <= LON_MAX:
            errors.append("longitude_out_of_bounds")

        if not is_finite_number(delay):
            errors.append("invalid_delay")
        elif float(delay) < 0:
            errors.append("negative_delay")

    if record_type == "events":
        for field in ("lat", "lon", "delay_seconds"):
            value = record.get(field)
            if value is not None and not is_finite_number(value):
                errors.append(f"invalid_{field}")

        if is_finite_number(record.get("lat")):
            if not LAT_MIN <= float(record["lat"]) <= LAT_MAX:
                errors.append("latitude_out_of_bounds")

        if is_finite_number(record.get("lon")):
            if not LON_MIN <= float(record["lon"]) <= LON_MAX:
                errors.append("longitude_out_of_bounds")

        if is_finite_number(record.get("delay_seconds")):
            if float(record["delay_seconds"]) < 0:
                errors.append("negative_delay")

    return errors


def validate_batch(records, record_type):
    """Separate valid and invalid records in a batch."""
    valid = []
    rejected = []

    for record in records:
        errors = validate_record(record, record_type)

        if errors:
            rejected.append({
                "record_type": record_type,
                "record": record,
                "errors": errors,
            })
        else:
            valid.append(record)

    return valid, rejected