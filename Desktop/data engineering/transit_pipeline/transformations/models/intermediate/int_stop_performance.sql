-- ═══════════════════════════════════════════════════════════════════════════
-- int_stop_performance.sql — Intermediate: Per-stop event performance
-- Layer: Intermediate (int_*)
-- Source: stg_events, routes
-- Depends on: stg_events
-- ═══════════════════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS int_stop_performance;

CREATE TABLE int_stop_performance AS
SELECT
    e.stop_id,
    e.route_id,
    r.name                          AS route_name,
    r.vehicle_type,
    -- Arrival stats
    COUNT(CASE WHEN e.event_type = 'stop_arrival' THEN 1 END)    AS total_arrivals,
    COUNT(CASE WHEN e.event_type = 'stop_departure' THEN 1 END)  AS total_departures,
    -- Delay metrics at this stop
    ROUND(AVG(e.delay_seconds), 1)                               AS avg_delay_s,
    MAX(e.delay_seconds)                                         AS max_delay_s,
    MIN(e.delay_seconds)                                         AS min_delay_s,
    -- On-time performance
    ROUND(
        100.0 * COUNT(CASE WHEN e.delay_severity = 'on_time' THEN 1 END)
        / MAX(COUNT(*), 1),
        1
    )                                                            AS on_time_pct,
    -- Peak period distribution
    COUNT(CASE WHEN e.time_period = 'morning_peak' THEN 1 END)   AS morning_peak_events,
    COUNT(CASE WHEN e.time_period = 'evening_peak' THEN 1 END)   AS evening_peak_events,
    COUNT(CASE WHEN e.time_period = 'off_peak' THEN 1 END)       AS off_peak_events,
    -- Total events
    COUNT(*)                                                     AS total_events,
    -- Latest activity
    MAX(e.event_timestamp)                                       AS last_activity
FROM stg_events e
JOIN routes r ON e.route_id = r.route_id
WHERE e.stop_id IS NOT NULL
GROUP BY e.stop_id, e.route_id, r.name, r.vehicle_type;
