"""
pipeline.py — Orchestrator for the transit data pipeline.

Runs the simulation + processing loop, persists data to SQLite,
and writes periodic analytics snapshots.

Usage:
    python pipeline.py                  # run indefinitely
    python pipeline.py --duration 60    # run for N seconds then exit
    python pipeline.py --demo           # run 30s with summary at end
"""

import argparse
import logging
import signal
import sys
import time
import threading
from datetime import datetime

from config import ROUTES, SIMULATION_TICK_SECONDS, ANALYTICS_SNAPSHOT_INTERVAL
import database as db
from simulator import TransitSimulator
from processor import build_snapshot
from etl import ETLPipeline
from validation import MovementValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


class TransitPipeline:
    """
    Coordinates simulation → processing → storage loop.

    Thread-safe: can be started in background thread while
    the Streamlit dashboard reads from the same SQLite DB.
    """

    def __init__(self, time_acceleration: float = 60.0):
        self.time_acceleration   = time_acceleration
        self._running            = False
        self._thread: threading.Thread | None = None
        self._snapshot_counter   = 0
        self._ticks_per_snapshot = max(1, int(ANALYTICS_SNAPSHOT_INTERVAL / SIMULATION_TICK_SECONDS))
        self._etl                = ETLPipeline(max_retries=3, retry_wait=0.5)
        self._validator          = MovementValidator()

    def start(self, blocking: bool = True) -> None:
        """Start the pipeline. If blocking=False, runs in background thread."""
        db.init_db()
        db.complete_stale_vehicles()
        db.upsert_routes(ROUTES)

        self.sim    = TransitSimulator(time_acceleration=self.time_acceleration)
        self._running = True

        logger.info("Pipeline started. Sim time: %s | Acceleration: %dx",
                    self.sim.sim_time.strftime("%H:%M:%S"), int(self.time_acceleration))

        if blocking:
            self._loop()
        else:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            logger.info("Pipeline running in background thread.")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Pipeline stopped.")

    def _loop(self) -> None:
        while self._running:
            tick_start = time.perf_counter()

            try:
                result = self.sim.tick()

                # Self-healing ETL: validate, deduplicate, retry, quarantine
                etl_stats = self._etl.run_tick(result)
                logger.debug(
                    "ETL tick | in=%d out=%d rejected=%d retries=%d",
                    etl_stats["records_in"], etl_stats["records_out"],
                    etl_stats["records_rejected"], etl_stats["retries"],
                )

                # Vehicle movement validation
                dt = SIMULATION_TICK_SECONDS * self.time_acceleration
                val_warnings = self._validator.validate_tick(
                    result["vehicles"], result["trips"],
                    result["events"], dt,
                )
                if val_warnings:
                    errors = [w for w in val_warnings if w.severity == "error"]
                    if errors:
                        logger.warning(
                            "[validation] %d error(s) in tick: %s",
                            len(errors),
                            "; ".join(w.message for w in errors[:3]),
                        )

                self._snapshot_counter += 1
                if self._snapshot_counter >= self._ticks_per_snapshot:
                    snap = build_snapshot(result["vehicles"], result["trips"], result["sim_time"])
                    db.insert_snapshot(snap)
                    self._snapshot_counter = 0
                    logger.debug(
                        "Snapshot saved. Sim: %s | Vehicles: %d | Avg delay: %.0fs",
                        result["sim_time"].strftime("%H:%M:%S"),
                        snap["total_vehicles"],
                        snap["avg_delay_seconds"],
                    )

            except Exception as exc:
                logger.exception("Unhandled error in pipeline tick: %s", exc)

            # Sleep for real-time tick interval
            elapsed = time.perf_counter() - tick_start
            sleep_s = max(0, SIMULATION_TICK_SECONDS - elapsed)
            time.sleep(sleep_s)


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry-point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Transit Data Pipeline")
    parser.add_argument("--duration",      type=int,   default=None,
                        help="Run for N seconds then exit (default: run forever)")
    parser.add_argument("--demo",          action="store_true",
                        help="Run 30s demo and print final summary")
    parser.add_argument("--acceleration",  type=float, default=60.0,
                        help="Simulation time acceleration factor (default: 60)")
    args = parser.parse_args()

    if args.demo:
        args.duration = 30

    pipeline = TransitPipeline(time_acceleration=args.acceleration)

    # Graceful shutdown
    def _handler(sig, frame):
        logger.info("Shutdown signal received.")
        pipeline.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _handler)
    signal.signal(signal.SIGTERM, _handler)

    if args.duration:
        pipeline.start(blocking=False)
        logger.info("Running for %d seconds…", args.duration)
        time.sleep(args.duration)
        pipeline.stop()

        # Print summary
        from analytics import get_summary_kpis, get_route_performance_leaderboard
        kpis = get_summary_kpis()
        print("\n" + "═" * 60)
        print("  TRANSIT PIPELINE DEMO — FINAL SUMMARY")
        print("═" * 60)
        print(f"  Sim Time       : {pipeline.sim.sim_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Period         : {kpis['peak_label']}")
        print(f"  Active Vehicles: {kpis['total_vehicles']}  "
              f"(\U0001f68c {kpis['buses']} buses, \U0001f687 {kpis['trains']} metro)")
        print(f"  Active Routes  : {kpis['active_routes']}")
        print(f"  Avg Delay      : {kpis['avg_delay_s']:.0f}s")
        print(f"  On-Time Rate   : {kpis['on_time_pct']:.1f}%")
        print(f"  Trips Completed: {kpis['trips_completed']}")
        print("─" * 60)

        lb = get_route_performance_leaderboard()
        if not lb.empty:
            print("  ROUTE PERFORMANCE LEADERBOARD")
            print(f"  {'#':<3} {'Route':<30} {'Score':>5} {'On-Time%':>8} {'Avg Delay':>10}")
            print("  " + "─" * 58)
            for rank, row in lb.head(9).iterrows():
                print(f"  {rank:<3} {row['route_name']:<30} {row['perf_score']:>5.1f} "
                      f"{row['on_time_pct']:>8.1f}% {row['avg_delay_s']:>9.0f}s")
        print("═" * 60)
        print(f"\nDatabase: {db.DB_PATH}")
        print("To launch dashboard: streamlit run dashboard.py\n")

    else:
        logger.info("Starting pipeline (Ctrl+C to stop)…")
        pipeline.start(blocking=True)


if __name__ == "__main__":
    main()
