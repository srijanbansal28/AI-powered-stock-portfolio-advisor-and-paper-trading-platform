-- ═══════════════════════════════════════════════════════════════════════════
-- int_vehicle_delays.sql — Intermediate: Vehicle delay analysis
-- Layer: Intermediate (int_*)
-- Source: stg_vehicles, stg_events
-- Depends on: stg_vehicles, stg_events
-- ═══════════════════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS int_vehicle_delays;

CREATE TABLE int_vehicle_delays AS
SELECT
    v.vehicle_id,
    v.route_id,
    v.vehicle_type,
    v.operator,
    v.delay_category,
    v.delay_seconds,
    v.speed_kmh,
    v.occupancy_pct,
    v.crowding_level,
    v.latitude,
    v.longitude,
    v.last_updated,
    -- Count of delay events per vehicle (last 500 events)
    COALESCE(delay_events.delay_event_count, 0)   AS delay_event_count,
    -- Average delay from event stream
    COALESCE(delay_events.avg_event_delay, 0)      AS avg_event_delay_s,
    -- Max delay from event stream
    COALESCE(delay_events.max_event_delay, 0)      AS max_event_delay_s,
    -- Delay trend: positive means worsening
    v.delay_seconds - COALESCE(delay_events.avg_event_delay, v.delay_seconds) AS delay_trend_s
FROM stg_vehicles v
LEFT JOIN (
    SELECT
        vehicle_id,
        COUNT(*)                     AS delay_event_count,
        ROUND(AVG(delay_seconds), 1) AS avg_event_delay,
        MAX(delay_seconds)           AS max_event_delay
    FROM stg_events
    WHERE event_type = 'delay'
       OR delay_seconds > 60
    GROUP BY vehicle_id
) delay_events ON v.vehicle_id = delay_events.vehicle_id;
