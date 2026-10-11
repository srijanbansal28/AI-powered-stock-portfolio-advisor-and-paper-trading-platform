-- ═══════════════════════════════════════════════════════════════════════════
-- stg_events.sql — Staging: Clean typed view of raw events stream
-- Layer: Staging (stg_*)
-- Source: events (Raw Data — Node C)
-- Target: stg_events (Clean Data — Node E)
-- ═══════════════════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS stg_events;

CREATE TABLE stg_events AS
SELECT
    event_id,
    event_type,
    vehicle_id,
    route_id,
    trip_id,
    stop_id,
    CAST(lat AS REAL)               AS latitude,
    CAST(lon AS REAL)               AS longitude,
    CAST(delay_seconds AS REAL)     AS delay_seconds,
    metadata_json,
    timestamp                       AS event_timestamp,
    -- Derived: extract date and hour for partitioning
    DATE(timestamp)                 AS event_date,
    CAST(STRFTIME('%H', timestamp) AS INTEGER) AS event_hour,
    -- Derived: time-of-day period
    CASE
        WHEN CAST(STRFTIME('%H', timestamp) AS INTEGER) BETWEEN 7 AND 10  THEN 'morning_peak'
        WHEN CAST(STRFTIME('%H', timestamp) AS INTEGER) BETWEEN 17 AND 20 THEN 'evening_peak'
        WHEN CAST(STRFTIME('%H', timestamp) AS INTEGER) BETWEEN 22 AND 23
          OR CAST(STRFTIME('%H', timestamp) AS INTEGER) BETWEEN 0 AND 5   THEN 'night'
        ELSE 'off_peak'
    END                             AS time_period,
    -- Derived: delay severity
    CASE
        WHEN CAST(delay_seconds AS REAL) <= 60  THEN 'on_time'
        WHEN CAST(delay_seconds AS REAL) <= 300 THEN 'moderate'
        ELSE 'severe'
    END                             AS delay_severity
FROM events
WHERE event_type IS NOT NULL
  AND vehicle_id IS NOT NULL
  AND route_id IS NOT NULL;
