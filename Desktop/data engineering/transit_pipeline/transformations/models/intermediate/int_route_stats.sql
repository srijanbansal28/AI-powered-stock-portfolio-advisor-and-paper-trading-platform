-- ═══════════════════════════════════════════════════════════════════════════
-- int_route_stats.sql — Intermediate: Per-route aggregate statistics
-- Layer: Intermediate (int_*)
-- Source: stg_trips, stg_vehicles, routes
-- Depends on: stg_trips, stg_vehicles
-- ═══════════════════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS int_route_stats;

CREATE TABLE int_route_stats AS
SELECT
    r.route_id,
    r.name                              AS route_name,
    r.vehicle_type,
    r.color                             AS route_color,
    -- Vehicle stats (current state)
    COALESCE(vs.active_vehicles, 0)     AS active_vehicles,
    COALESCE(vs.avg_vehicle_delay_s, 0) AS avg_vehicle_delay_s,
    COALESCE(vs.avg_occupancy_pct, 0)   AS avg_occupancy_pct,
    COALESCE(vs.avg_speed_kmh, 0)       AS avg_speed_kmh,
    -- Trip stats (historical)
    COALESCE(ts.total_trips, 0)         AS total_trips,
    COALESCE(ts.completed_trips, 0)     AS completed_trips,
    COALESCE(ts.avg_trip_delay_s, 0)    AS avg_trip_delay_s,
    COALESCE(ts.avg_trip_duration_min, 0) AS avg_trip_duration_min,
    COALESCE(ts.on_time_pct, 0)         AS on_time_pct,
    -- Performance score (weighted composite)
    ROUND(
        COALESCE(ts.on_time_pct, 50) * 0.6
        + (100 - MIN(COALESCE(vs.avg_vehicle_delay_s, 0) / 3.0, 100)) * 0.4,
        1
    )                                   AS performance_score
FROM routes r
LEFT JOIN (
    SELECT
        route_id,
        COUNT(*)                            AS active_vehicles,
        ROUND(AVG(delay_seconds), 1)        AS avg_vehicle_delay_s,
        ROUND(AVG(occupancy_pct) * 100, 1)  AS avg_occupancy_pct,
        ROUND(AVG(speed_kmh), 1)            AS avg_speed_kmh
    FROM stg_vehicles
    WHERE status IN ('in_transit', 'at_stop', 'delayed')
    GROUP BY route_id
) vs ON r.route_id = vs.route_id
LEFT JOIN (
    SELECT
        route_id,
        COUNT(*)                                                    AS total_trips,
        COUNT(CASE WHEN status = 'completed' THEN 1 END)           AS completed_trips,
        ROUND(AVG(delay_seconds), 1)                                AS avg_trip_delay_s,
        ROUND(AVG(duration_minutes), 1)                             AS avg_trip_duration_min,
        ROUND(100.0 * SUM(is_on_time) / MAX(COUNT(*), 1), 1)       AS on_time_pct
    FROM stg_trips
    GROUP BY route_id
) ts ON r.route_id = ts.route_id;
