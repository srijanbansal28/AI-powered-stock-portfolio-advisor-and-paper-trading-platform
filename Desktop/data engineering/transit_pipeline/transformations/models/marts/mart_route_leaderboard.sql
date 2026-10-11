-- ═══════════════════════════════════════════════════════════════════════════
-- mart_route_leaderboard.sql — Mart: Route performance leaderboard
-- Layer: Marts (mart_*)
-- Architecture: Node H — Analytics Tables
-- Source: int_route_stats
-- ═══════════════════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS mart_route_leaderboard;

CREATE TABLE mart_route_leaderboard AS
SELECT
    route_id,
    route_name,
    vehicle_type,
    route_color,
    active_vehicles,
    total_trips,
    completed_trips,
    on_time_pct,
    avg_vehicle_delay_s,
    avg_trip_delay_s,
    avg_trip_duration_min,
    avg_occupancy_pct,
    avg_speed_kmh,
    performance_score,
    -- Ranking
    RANK() OVER (ORDER BY performance_score DESC)                AS overall_rank,
    RANK() OVER (PARTITION BY vehicle_type ORDER BY performance_score DESC) AS type_rank,
    -- Tier classification
    CASE
        WHEN performance_score >= 80 THEN '🟢 Excellent'
        WHEN performance_score >= 60 THEN '🟡 Good'
        WHEN performance_score >= 40 THEN '🟠 Fair'
        ELSE '🔴 Poor'
    END                                                          AS performance_tier,
    -- Service reliability index (trips completed / total trips)
    CASE
        WHEN total_trips > 0
        THEN ROUND(100.0 * completed_trips / total_trips, 1)
        ELSE 0
    END                                                          AS reliability_pct,
    DATETIME('now')                                              AS computed_at
FROM int_route_stats
ORDER BY performance_score DESC;
