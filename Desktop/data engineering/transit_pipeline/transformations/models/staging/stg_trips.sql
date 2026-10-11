-- ═══════════════════════════════════════════════════════════════════════════
-- stg_trips.sql — Staging: Clean typed view of raw trips table
-- Layer: Staging (stg_*)
-- Source: trips (Raw Data — Node C)
-- Target: stg_trips (Clean Data — Node E)
-- ═══════════════════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS stg_trips;

CREATE TABLE stg_trips AS
SELECT
    trip_id,
    vehicle_id,
    route_id,
    scheduled_departure,
    actual_departure,
    scheduled_arrival,
    actual_arrival,
    CAST(delay_seconds AS REAL)     AS delay_seconds,
    CAST(duration_seconds AS REAL)  AS duration_seconds,
    CAST(stops_visited AS INTEGER)  AS stops_visited,
    CAST(total_stops AS INTEGER)    AS total_stops,
    status,
    created_at,
    -- Derived: trip completion ratio
    CASE
        WHEN CAST(total_stops AS INTEGER) > 0
        THEN ROUND(CAST(stops_visited AS REAL) / CAST(total_stops AS REAL) * 100, 1)
        ELSE 0
    END                             AS completion_pct,
    -- Derived: is on time
    CASE
        WHEN CAST(delay_seconds AS REAL) <= 60 THEN 1
        ELSE 0
    END                             AS is_on_time,
    -- Derived: duration in minutes
    ROUND(CAST(duration_seconds AS REAL) / 60.0, 1) AS duration_minutes,
    -- Derived: date
    DATE(created_at)                AS trip_date
FROM trips
WHERE trip_id IS NOT NULL
  AND route_id IS NOT NULL;
