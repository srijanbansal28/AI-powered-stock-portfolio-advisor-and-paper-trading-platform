"""
test_bengaluru_transit.py — Validation test suite for Bengaluru transit update.
"""

import math
import unittest
import pandas as pd
import plotly.graph_objects as go

import config
import database as db
from simulator import TransitSimulator, haversine
from processor import compute_route_performance, build_snapshot, build_departure_board
import analytics as ana


class TestBengaluruTransit(unittest.TestCase):

    def test_routes_exist_and_preserved(self):
        expected_ids = {
            "BUS-101", "BUS-102", "BUS-103", "BUS-104", "BUS-105", "BUS-106",
            "Metro-L1", "Metro-L2", "Metro-L3"
        }
        actual_ids = {r.route_id for r in config.ROUTES}
        self.assertEqual(expected_ids, actual_ids, "All route IDs must be preserved")

    def test_all_stops_within_bengaluru_bounds(self):
        # Bounding box for greater Bengaluru urban area
        BENGALURU_LAT_MIN = 12.70
        BENGALURU_LAT_MAX = 13.35
        BENGALURU_LON_MIN = 77.35
        BENGALURU_LON_MAX = 77.85

        for route in config.ROUTES:
            self.assertGreater(len(route.stops), 1, f"Route {route.route_id} must have multiple stops")
            for stop in route.stops:
                self.assertGreaterEqual(
                    stop.lat, BENGALURU_LAT_MIN,
                    f"Stop {stop.name} lat {stop.lat} below Bengaluru south limit"
                )
                self.assertLessEqual(
                    stop.lat, BENGALURU_LAT_MAX,
                    f"Stop {stop.name} lat {stop.lat} above Bengaluru north limit"
                )
                self.assertGreaterEqual(
                    stop.lon, BENGALURU_LON_MIN,
                    f"Stop {stop.name} lon {stop.lon} west of Bengaluru limit"
                )
                self.assertLessEqual(
                    stop.lon, BENGALURU_LON_MAX,
                    f"Stop {stop.name} lon {stop.lon} east of Bengaluru limit"
                )

    def test_no_legacy_mumbai_names_remain(self):
        mumbai_terms = ["CST", "Bandra", "Andheri", "Borivali", "Churchgate", "Navi Mumbai", "Dadar", "Worli"]
        for route in config.ROUTES:
            for term in mumbai_terms:
                self.assertNotIn(
                    term.lower(), route.name.lower(),
                    f"Legacy Mumbai term '{term}' found in route name: {route.name}"
                )
            for stop in route.stops:
                for term in mumbai_terms:
                    self.assertNotIn(
                        term.lower(), stop.name.lower(),
                        f"Legacy Mumbai term '{term}' found in stop name: {stop.name}"
                    )

    def test_metro_station_sequences_and_distances(self):
        purple_line = config.ROUTE_BY_ID["Metro-L1"]
        green_line = config.ROUTE_BY_ID["Metro-L2"]
        yellow_line = config.ROUTE_BY_ID["Metro-L3"]

        self.assertEqual(len(purple_line.stops), 37, "Purple line must have 37 stations")
        self.assertEqual(purple_line.stops[0].name, "Challaghatta")
        self.assertEqual(purple_line.stops[-1].name, "Whitefield (Kadugodi)")

        self.assertEqual(len(green_line.stops), 32, "Green line must have 32 stations")
        self.assertEqual(green_line.stops[0].name, "Madavara")
        self.assertEqual(green_line.stops[-1].name, "Silk Institute")

        self.assertEqual(len(yellow_line.stops), 16, "Yellow line must have 16 stations")
        self.assertEqual(yellow_line.stops[0].name, "Rashtreeya Vidyalaya Road")
        self.assertEqual(yellow_line.stops[-1].name, "Bommasandra")

        # Verify inter-station segment distances are reasonable
        for route in [purple_line, green_line, yellow_line]:
            for i in range(len(route.stops) - 1):
                d = haversine(
                    route.stops[i].lat, route.stops[i].lon,
                    route.stops[i+1].lat, route.stops[i+1].lon
                )
                self.assertGreater(d, 0.2, f"{route.name}: Segment {i} distance {d:.2f}km too short")
                self.assertLess(d, 6.0, f"{route.name}: Segment {i} distance {d:.2f}km too long")

    def test_dataclasses_integrity(self):
        # Stop dataclass attributes
        stop = config.Stop("TEST", "Test Stop", 12.97, 77.59)
        self.assertEqual(stop.stop_id, "TEST")
        self.assertEqual(stop.name, "Test Stop")
        self.assertEqual(stop.lat, 12.97)
        self.assertEqual(stop.lon, 77.59)

        # Route dataclass attributes
        route = config.ROUTES[0]
        self.assertTrue(hasattr(route, "route_id"))
        self.assertTrue(hasattr(route, "name"))
        self.assertTrue(hasattr(route, "vehicle_type"))
        self.assertTrue(hasattr(route, "color"))
        self.assertTrue(hasattr(route, "stops"))
        self.assertTrue(hasattr(route, "headway_minutes"))
        self.assertTrue(hasattr(route, "first_departure"))
        self.assertTrue(hasattr(route, "last_departure"))
        self.assertTrue(hasattr(route, "avg_speed_kmh"))

    def test_database_reset_and_no_legacy(self):
        self.assertFalse(db.is_legacy_database(), "Database must not contain legacy Mumbai data")
        routes = db.get_route_list()
        self.assertEqual(len(routes), 9, "Database must store all 9 Bengaluru routes")

    def test_simulator_and_processor_integration(self):
        sim = TransitSimulator(time_acceleration=60.0)
        # Run 3 simulation ticks
        res1 = sim.tick()
        res2 = sim.tick()
        res3 = sim.tick()

        self.assertIn("vehicles", res3)
        self.assertIn("trips", res3)
        self.assertIn("events", res3)
        self.assertGreater(len(res3["vehicles"]), 0, "Vehicles must be active in simulation")

        # Verify vehicles are in Bengaluru
        for v in res3["vehicles"]:
            self.assertGreaterEqual(v["lat"], 12.70)
            self.assertLessEqual(v["lat"], 13.35)
            self.assertGreaterEqual(v["lon"], 77.35)
            self.assertLessEqual(v["lon"], 77.85)

        # Test snapshot builder
        snap = build_snapshot(res3["vehicles"], res3["trips"], res3["sim_time"])
        self.assertGreater(snap["total_vehicles"], 0)
        self.assertIn("metrics_json", snap)

        # Test route performance
        perf = compute_route_performance(res3["vehicles"])
        self.assertIsInstance(perf, dict)

    def test_departure_board(self):
        sim = TransitSimulator(time_acceleration=60.0)
        res = sim.tick()
        # Test departure board for Majestic
        board = build_departure_board("101_S1", res["vehicles"], sim.sim_time)
        self.assertIsInstance(board, list)

    def test_plotly_scattermap_configuration(self):
        # Verify Plotly 7 Scattermap trace and layout works without error
        fig = go.Figure()
        fig.add_trace(go.Scattermap(
            lat=[12.9716, 12.9757],
            lon=[77.5946, 77.5728],
            mode="markers+lines",
            name="Test Bengaluru Trace"
        ))
        fig.update_layout(
            map=dict(
                style="carto-darkmatter",
                center=dict(lat=12.9716, lon=77.5946),
                zoom=10.5,
            )
        )
        # Check dict representation
        d = fig.to_dict()
        self.assertIn("map", d["layout"])
        self.assertEqual(d["layout"]["map"]["center"]["lat"], 12.9716)
        self.assertEqual(d["layout"]["map"]["center"]["lon"], 77.5946)
        self.assertEqual(d["data"][0]["type"], "scattermap")


if __name__ == "__main__":
    unittest.main()
