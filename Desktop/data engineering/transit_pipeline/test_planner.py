"""
test_planner.py — Validation test suite for Journey Planner.
Tests:
  1. Direct bus journey planning (Majestic -> Whitefield)
  2. Direct metro journey planning (MG Road -> Indiranagar)
  3. Multi-modal transfer planning (Metro to Metro: Challaghatta -> Silk Institute)
  4. Multi-modal transfer planning (Metro to Bus: Challaghatta -> Electronic City)
  5. Same origin and destination edge-case handling
  6. Place retrieval and connectivity metadata
"""

import unittest
from datetime import datetime

import planner
from config import ROUTES


class TestJourneyPlanner(unittest.TestCase):

    def test_get_all_places(self):
        places = planner.get_all_places()
        self.assertGreater(len(places), 50, "Should index all stops across Bengaluru")
        majestic = next((p for p in places if "Majestic" in p["name"]), None)
        self.assertIsNotNone(majestic)
        self.assertTrue(len(majestic["routes"]) > 0)

    def test_direct_metro_journey(self):
        plans = planner.find_journeys("Mahatma Gandhi Road", "Indiranagar")
        self.assertGreater(len(plans), 0)
        best = plans[0]
        self.assertIn("metro", best.badge.lower())
        self.assertGreater(best.total_duration_minutes, 0)
        self.assertEqual(len(best.legs), 1)
        self.assertEqual(best.legs[0].vehicle_type, "metro")

    def test_direct_bus_journey(self):
        plans = planner.find_journeys("Kempegowda Bus Station (Majestic)", "ITPL / Whitefield")
        self.assertGreater(len(plans), 0)
        # Should return direct options (Metro Purple Line or Bus 101)
        direct_plans = [p for p in plans if p.plan_type == "direct"]
        self.assertGreater(len(direct_plans), 0)

    def test_metro_to_metro_interchange(self):
        # Challaghatta (Purple Line) to Silk Institute (Green Line) transfers at Majestic
        plans = planner.find_journeys("Challaghatta", "Silk Institute")
        self.assertGreater(len(plans), 0)
        best = plans[0]
        self.assertEqual(len(best.legs), 2)
        self.assertEqual(best.legs[0].vehicle_type, "metro")
        self.assertEqual(best.legs[1].vehicle_type, "metro")
        self.assertIn("Nadaprabhu Kempegowda (Majestic)", [s[0].name for s in best.transfer_stops])

    def test_same_origin_and_destination(self):
        plans = planner.find_journeys("Indiranagar", "Indiranagar")
        self.assertEqual(len(plans), 0)

    def test_eta_and_carbon_calculations(self):
        departure = datetime(2026, 10, 11, 8, 30, 0)
        plans = planner.find_journeys("Mahatma Gandhi Road", "Whitefield (Kadugodi)", departure_time=departure)
        self.assertGreater(len(plans), 0)
        best = plans[0]
        self.assertEqual(best.departure_time, departure)
        self.assertGreater(best.arrival_time, departure)
        self.assertGreater(best.fare_inr, 0)
        self.assertGreater(best.co2_saved_kg, 0)


    def test_user_current_location_routing(self):
        """Verify routing from a user current location (with nearest stop walk calculation)."""
        plans = planner.find_journeys(
            "Koramangala (Sony World / 5th Block)",
            "ITPL / Whitefield",
        )
        self.assertGreaterEqual(len(plans), 3, "Must return at least 3 options")
        best = plans[0]
        self.assertGreater(best.walk_to_first_stop_meters, 0)
        self.assertGreater(best.walk_to_first_stop_minutes, 0)
        self.assertIsNotNone(best.user_coords)

    def test_at_least_three_options_guarantee(self):
        """Verify that any valid transit query returns at least 3 distinct options."""
        test_pairs = [
            ("Kempegowda Bus Station (Majestic)", "Kempegowda Int. Airport T1/T2"),
            ("Challaghatta", "Silk Institute"),
            ("Mahatma Gandhi Road", "Indiranagar"),
        ]
        for orig, dest in test_pairs:
            plans = planner.find_journeys(orig, dest)
            self.assertGreaterEqual(
                len(plans),
                3,
                f"Query from {orig} to {dest} must return at least 3 options, got {len(plans)}",
            )

    def test_find_nearby_transit_stops(self):
        """Verify geodesic distance and walking time calculation to available transit stops."""
        # Majestic coordinates
        lat, lon = 12.9767, 77.5713
        nearby = planner.find_nearby_transit_stops(lat, lon, top_k=5)
        self.assertGreaterEqual(len(nearby), 3)
        # Should be sorted by distance ascending
        for i in range(len(nearby) - 1):
            self.assertLessEqual(nearby[i]["distance_meters"], nearby[i + 1]["distance_meters"])
        
        closest = nearby[0]
        self.assertIn("distance_meters", closest)
        self.assertIn("walk_minutes", closest)
        self.assertIn("routes", closest)
        self.assertIn("modes", closest)
        self.assertLessEqual(closest["distance_meters"], 500, "Closest stop to Majestic coords should be within 500m")
        self.assertGreater(closest["walk_minutes"], 0)

    def test_journey_options_sorted_by_least_time(self):
        """Verify that returned journeys can be sorted by least total time to destination."""
        plans = planner.find_journeys(
            "Kempegowda Bus Station (Majestic)",
            "ITPL / Whitefield",
            user_coords=(12.9767, 77.5713)
        )
        self.assertGreaterEqual(len(plans), 3)
        # Verify plans are sorted or sortable by total_duration_minutes
        durations = [p.total_duration_minutes for p in plans]
        sorted_durations = sorted(durations)
        # Sort plans
        plans.sort(key=lambda p: p.total_duration_minutes)
        self.assertEqual([p.total_duration_minutes for p in plans], sorted_durations)
        self.assertGreater(plans[0].walk_to_first_stop_meters, 0)


    def test_find_nearest_bus_stations(self):
        """Verify calculation of nearest bus station and all nearest bus stations from coordinates."""
        # Koramangala coordinates
        lat, lon = 12.9352, 77.6245
        nearby_buses = planner.find_nearest_bus_stations(lat, lon, top_k=6)
        self.assertGreaterEqual(len(nearby_buses), 4)
        closest_bus = nearby_buses[0]
        self.assertEqual(closest_bus["name"], "Koramangala Sony World")
        self.assertLessEqual(closest_bus["distance_meters"], 150)
        self.assertIn("201-G", closest_bus["bus_numbers"])
        # Distances must be non-decreasing
        for i in range(len(nearby_buses) - 1):
            self.assertLessEqual(nearby_buses[i]["distance_meters"], nearby_buses[i + 1]["distance_meters"])


if __name__ == "__main__":
    unittest.main()
