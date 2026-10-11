-- ═══════════════════════════════════════════════════════════════════════════
-- mart_hourly_analytics.sql — Mart: Hourly transit KPIs
-- Layer: Marts (mart_*)
-- Architecture: Node H — Analytics Tables
-- Source: stg_events, stg_vehicles
-- ═══════════════════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS mart_hourly_analytics;

CREATE TABLE mart_hourly_analytics AS
SELECT
    event_date,
    event_hour,
    time_period,
    -- Volume metrics
    COUNT(*)                                                     AS total_events,
    COUNT(DISTINCT vehicle_id)                                   AS unique_vehicles,
    COUNT(DISTINCT route_id)                                     AS active_routes,
    -- Event type breakdown
    COUNT(CASE WHEN event_type = 'position_update' THEN 1 END)   AS position_updates,
    COUNT(CASE WHEN event_type = 'stop_arrival' THEN 1 END)      AS stop_arrivals,
    COUNT(CASE WHEN event_type = 'stop_departure' THEN 1 END)    AS stop_departures,
    COUNT(CASE WHEN event_type = 'delay' THEN 1 END)             AS delay_events,
    -- Delay metrics
    ROUND(AVG(delay_seconds), 1)                                 AS avg_delay_s,
    MAX(delay_seconds)                                           AS max_delay_s,
    -- On-time performance
    ROUND(
        100.0 * COUNT(CASE WHEN delay_severity = 'on_time' THEN 1 END)
        / MAX(COUNT(*), 1),
        1
    )                                                            AS on_time_pct,
    -- Severity breakdown
    COUNT(CASE WHEN delay_severity = 'on_time' THEN 1 END)      AS on_time_count,
    COUNT(CASE WHEN delay_severity = 'moderate' THEN 1 END)      AS moderate_delay_count,
    COUNT(CASE WHEN delay_severity = 'severe' THEN 1 END)        AS severe_delay_count,
    -- Metadata
    MIN(event_timestamp)                                         AS first_event,
    MAX(event_timestamp)                                         AS last_event
FROM stg_events
GROUP BY event_date, event_hour, time_period
ORDER BY event_date, event_hour;
