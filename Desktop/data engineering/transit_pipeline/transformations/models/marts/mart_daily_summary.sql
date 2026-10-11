-- ═══════════════════════════════════════════════════════════════════════════
-- mart_daily_summary.sql — Mart: Daily operational summary
-- Layer: Marts (mart_*)
-- Architecture: Node H — Analytics Tables
-- Source: stg_trips, stg_events, etl_run_log
-- ═══════════════════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS mart_daily_summary;

CREATE TABLE mart_daily_summary AS
SELECT
    t.trip_date                                              AS report_date,
    -- Trip metrics
    COUNT(DISTINCT t.trip_id)                                AS total_trips,
    COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.trip_id END) AS completed_trips,
    COUNT(DISTINCT CASE WHEN t.status = 'in_progress' THEN t.trip_id END) AS active_trips,
    COUNT(DISTINCT t.vehicle_id)                             AS unique_vehicles,
    COUNT(DISTINCT t.route_id)                               AS routes_served,
    -- Delay metrics
    ROUND(AVG(t.delay_seconds), 1)                           AS avg_delay_s,
    MAX(t.delay_seconds)                                     AS max_delay_s,
    ROUND(100.0 * SUM(t.is_on_time) / MAX(COUNT(*), 1), 1)  AS on_time_pct,
    -- Duration metrics
    ROUND(AVG(t.duration_minutes), 1)                        AS avg_trip_duration_min,
    ROUND(SUM(t.duration_minutes), 1)                        AS total_service_minutes,
    -- Completion metrics
    ROUND(AVG(t.completion_pct), 1)                          AS avg_completion_pct,
    -- Event volume (from events table)
    COALESCE(ev.total_events, 0)                             AS total_events,
    COALESCE(ev.position_updates, 0)                         AS position_updates,
    COALESCE(ev.stop_events, 0)                              AS stop_events,
    -- Pipeline health (from etl_run_log)
    COALESCE(etl.total_pipeline_runs, 0)                     AS pipeline_runs,
    COALESCE(etl.successful_runs, 0)                         AS successful_pipeline_runs,
    COALESCE(etl.total_rows_ingested, 0)                     AS rows_ingested,
    COALESCE(etl.total_rows_rejected, 0)                     AS rows_rejected,
    -- Computed at
    DATETIME('now')                                          AS computed_at
FROM stg_trips t
LEFT JOIN (
    SELECT
        event_date,
        COUNT(*)                                              AS total_events,
        COUNT(CASE WHEN event_type = 'position_update' THEN 1 END) AS position_updates,
        COUNT(CASE WHEN event_type IN ('stop_arrival', 'stop_departure') THEN 1 END) AS stop_events
    FROM stg_events
    GROUP BY event_date
) ev ON t.trip_date = ev.event_date
LEFT JOIN (
    SELECT
        DATE(started_at)                                      AS run_date,
        COUNT(*)                                               AS total_pipeline_runs,
        COUNT(CASE WHEN status = 'success' THEN 1 END)        AS successful_runs,
        SUM(COALESCE(records_out, 0))                          AS total_rows_ingested,
        SUM(COALESCE(records_rejected, 0))                     AS total_rows_rejected
    FROM etl_run_log
    GROUP BY DATE(started_at)
) etl ON t.trip_date = etl.run_date
GROUP BY t.trip_date
ORDER BY t.trip_date DESC;
