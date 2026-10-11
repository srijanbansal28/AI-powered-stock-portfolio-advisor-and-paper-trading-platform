-- ═══════════════════════════════════════════════════════════════════════════
-- stg_vehicles.sql — Staging: Clean typed view of raw vehicles table
-- Layer: Staging (stg_*)
-- Source: vehicles (Raw Data — Node C)
-- Target: stg_vehicles (Clean Data — Node E)
-- ═══════════════════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS stg_vehicles;

CREATE TABLE stg_vehicles AS
SELECT
    vehicle_id,
    route_id,
    trip_id,
    vehicle_type,
    status,
    current_stop_id,
    next_stop_id,
    CAST(lat AS REAL)               AS latitude,
    CAST(lon AS REAL)               AS longitude,
    CAST(speed_kmh AS REAL)         AS speed_kmh,
    CAST(delay_seconds AS REAL)     AS delay_seconds,
    CAST(occupancy AS REAL)         AS occupancy_pct,
    CAST(heading AS REAL)           AS heading_deg,
    last_updated,
    -- Derived columns
    CASE
        WHEN CAST(delay_seconds AS REAL) <= 60  THEN 'on_time'
        WHEN CAST(delay_seconds AS REAL) <= 300 THEN 'moderate_delay'
        ELSE 'severe_delay'
    END                             AS delay_category,
    CASE
        WHEN CAST(occupancy AS REAL) >= 0.85 THEN 'crowded'
        WHEN CAST(occupancy AS REAL) >= 0.50 THEN 'moderate'
        ELSE 'comfortable'
    END                             AS crowding_level,
    CASE
        WHEN vehicle_type = 'bus'   THEN 'BMTC'
        WHEN vehicle_type = 'train' THEN 'BMRCL'
        ELSE 'OTHER'
    END                             AS operator
FROM vehicles
WHERE lat IS NOT NULL
  AND lon IS NOT NULL
  AND vehicle_id IS NOT NULL;
