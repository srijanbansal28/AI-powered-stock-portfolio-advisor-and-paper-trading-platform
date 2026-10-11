"""
config.py — Static route/schedule configuration for the transit pipeline.

Defines 6 bus corridors and 3 metro lines with stops, coordinates, headways,
and simulation parameters for Bengaluru, Karnataka. Real Namma Metro corridors
follow verified station sequences, while simulation-specific links are labeled
as simulated. The pipeline architecture remains city-agnostic.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict

# ─────────────────────────────────────────────────────────────────────────────
# Simulation Settings
# ─────────────────────────────────────────────────────────────────────────────

SIMULATION_TICK_SECONDS = 5       # How often vehicles update their position
ANALYTICS_SNAPSHOT_INTERVAL = 60  # Seconds between KPI rollup snapshots
DB_PATH = "transit_pipeline/transit.db"

# Peak hour windows (24-h format)
PEAK_HOURS = {
    "morning": (7, 10),   # 7:00 AM – 10:00 AM
    "evening": (17, 20),  # 5:00 PM –  8:00 PM
}

# Delay parameters
DELAY_PROBABILITY_NORMAL = 0.25   # 25% chance of delay off-peak
DELAY_PROBABILITY_PEAK   = 0.55   # 55% chance during peak hours
DELAY_MEAN_SECONDS       = 120    # Mean delay ~2 min
DELAY_STD_SECONDS        = 180    # Std dev ~3 min (log-normal)

# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Stop:
    stop_id: str
    name: str
    lat: float
    lon: float


@dataclass
class Route:
    route_id: str
    name: str
    vehicle_type: str           # "bus" | "metro"
    color: str                  # hex color for map
    stops: List[Stop]
    headway_minutes: int        # Minutes between consecutive vehicles
    first_departure: str        # "HH:MM"
    last_departure: str         # "HH:MM"
    avg_speed_kmh: float        # Average speed between stops
    bus_number: str = ""        # e.g. "335-E", "500-D", "KIA-9", "Purple Line"
    display_name: str = ""      # e.g. "BMTC Volvo Vajra 335-E"
    destination_sign: str = ""  # e.g. "ITPL / Whitefield (via Marathahalli)"


# ─────────────────────────────────────────────────────────────────────────────
# Stop Definitions  (Bengaluru / Karnataka area)
# ─────────────────────────────────────────────────────────────────────────────

# --- Bus Route 101: Majestic → Whitefield (BMTC 335E Arterial Corridor) ---
BUS_101_STOPS = [
    Stop("101_S1", "Kempegowda Bus Station (Majestic)", 12.9772, 77.5713),
    Stop("101_S2", "Corporation (Hudson Circle)",       12.9698, 77.5878),
    Stop("101_S3", "Richmond Circle",                   12.9667, 77.5992),
    Stop("101_S4", "Mayo Hall (MG Road)",               12.9739, 77.6083),
    Stop("101_S5", "Domlur TTMC",                       12.9609, 77.6387),
    Stop("101_S6", "HAL Old Airport",                   12.9560, 77.6650),
    Stop("101_S7", "Marathahalli Bridge",               12.9562, 77.7011),
    Stop("101_S8", "Kundalahalli Gate",                 12.9658, 77.7185),
    Stop("101_S9", "ITPL / Whitefield",                 12.9866, 77.7380),
]

# --- Bus Route 102: Majestic → Electronic City (Hosur Road Corridor) ---
BUS_102_STOPS = [
    Stop("102_S1", "Kempegowda Bus Station (Majestic)", 12.9772, 77.5713),
    Stop("102_S2", "Corporation (Hudson Circle)",       12.9698, 77.5878),
    Stop("102_S3", "Dairy Circle",                      12.9385, 77.6000),
    Stop("102_S4", "St. John's Hospital",               12.9284, 77.6190),
    Stop("102_S5", "Central Silk Board",                12.9165, 77.6206),
    Stop("102_S6", "Bommanahalli",                      12.9085, 77.6255),
    Stop("102_S7", "Kudlu Gate",                        12.8899, 77.6393),
    Stop("102_S8", "Electronic City Toll Gate",         12.8480, 77.6680),
]

# --- Bus Route 103: Banashankari → Hebbal (ORR West / North Corridor) ---
BUS_103_STOPS = [
    Stop("103_S1", "Banashankari TTMC",                 12.9155, 77.5735),
    Stop("103_S2", "Kathriguppe",                       12.9240, 77.5510),
    Stop("103_S3", "Nayandahalli Junction",             12.9460, 77.5255),
    Stop("103_S4", "Vijayanagar TTMC",                  12.9680, 77.5360),
    Stop("103_S5", "Yeshwanthpur TTMC",                 13.0232, 77.5499),
    Stop("103_S6", "BEL Circle",                        13.0410, 77.5550),
    Stop("103_S7", "Hebbal TTMC",                       13.0358, 77.5970),
]

# --- Bus Route 104: ORR-Koramangala Loop (Simulated) ---
BUS_104_STOPS = [
    Stop("104_S1", "Central Silk Board",                12.9165, 77.6206),
    Stop("104_S2", "HSR Layout 5th Main",               12.9115, 77.6380),
    Stop("104_S3", "Bellandur EcoSpace",                12.9260, 77.6762),
    Stop("104_S4", "Marathahalli Junction",             12.9562, 77.7011),
    Stop("104_S5", "Domlur Flyover",                    12.9609, 77.6387),
    Stop("104_S6", "Koramangala Sony World",            12.9345, 77.6245),
    Stop("104_S7", "Central Silk Board",                12.9165, 77.6206),  # circular loop
]

# --- Bus Route 105: KIA Airport Express (Vayu Vajra KIA-9) ---
BUS_105_STOPS = [
    Stop("105_S1", "Kempegowda Int. Airport T1/T2",     13.1986, 77.7066),
    Stop("105_S2", "Trumpet Flyover",                   13.1550, 77.6400),
    Stop("105_S3", "Yelahanka Bypass",                  13.1007, 77.5963),
    Stop("105_S4", "Hebbal TTMC",                       13.0358, 77.5970),
    Stop("105_S5", "Mekhri Circle",                     13.0084, 77.5835),
    Stop("105_S6", "Kempegowda Bus Station (Majestic)", 12.9772, 77.5713),
]

# --- Bus Route 106: IT Corridor Connector (Simulated) ---
BUS_106_STOPS = [
    Stop("106_S1", "Whitefield ITPL",                   12.9866, 77.7380),
    Stop("106_S2", "Kundalahalli Gate",                 12.9658, 77.7185),
    Stop("106_S3", "Bellandur EcoSpace",                12.9260, 77.6762),
    Stop("106_S4", "Central Silk Board",                12.9165, 77.6206),
    Stop("106_S5", "Electronic City Phase 1",           12.8465, 77.6711),
]

# --- Metro Line L1: Namma Metro Purple Line (Challaghatta ↔ Whitefield) ---
Metro_L1_STOPS = [
    Stop("L1_S1",  "Challaghatta",                      12.8974, 77.4612),
    Stop("L1_S2",  "Kengeri",                           12.9080, 77.4765),
    Stop("L1_S3",  "Kengeri Bus Terminal",              12.9149, 77.4876),
    Stop("L1_S4",  "Pattanagere",                       12.9244, 77.4983),
    Stop("L1_S5",  "Jnanabharathi",                     12.9356, 77.5120),
    Stop("L1_S6",  "Rajarajeshwari Nagar",              12.9367, 77.5196),
    Stop("L1_S7",  "Nayandahalli",                      12.9460, 77.5255),
    Stop("L1_S8",  "Mysuru Road",                       12.9465, 77.5298),
    Stop("L1_S9",  "Deepanjali Nagar",                  12.9522, 77.5369),
    Stop("L1_S10", "Attiguppe",                         12.9610, 77.5530),
    Stop("L1_S11", "Vijayanagar",                       12.9680, 77.5615),
    Stop("L1_S12", "Hosahalli",                         12.9742, 77.5455),
    Stop("L1_S13", "Magadi Road",                       12.9756, 77.5554),
    Stop("L1_S14", "KSR Bengaluru (City Rly)",          12.9758, 77.5657),
    Stop("L1_S15", "Nadaprabhu Kempegowda (Majestic)",  12.9757, 77.5728),
    Stop("L1_S16", "Sir M. Visvesvaraya (Central)",     12.9738, 77.5835),
    Stop("L1_S17", "Dr. B.R. Ambedkar (Vidhana Soudha)",12.9798, 77.5927),
    Stop("L1_S18", "Cubbon Park",                       12.9811, 77.5969),
    Stop("L1_S19", "Mahatma Gandhi Road",               12.9755, 77.6068),
    Stop("L1_S20", "Trinity",                           12.9727, 77.6170),
    Stop("L1_S21", "Halasuru",                          12.9757, 77.6263),
    Stop("L1_S22", "Indiranagar",                       12.9783, 77.6387),
    Stop("L1_S23", "Swami Vivekananda Road",            12.9860, 77.6449),
    Stop("L1_S24", "Baiyappanahalli",                   12.9908, 77.6525),
    Stop("L1_S25", "Benniganahalli",                    12.9980, 77.6620),
    Stop("L1_S26", "Krishnarajapura (KR Pura)",         13.0000, 77.6779),
    Stop("L1_S27", "Singayyanapalya",                   12.9975, 77.6925),
    Stop("L1_S28", "Garudacharpalya",                   12.9922, 77.7020),
    Stop("L1_S29", "Hoodi",                             12.9897, 77.7145),
    Stop("L1_S30", "Seetharamapalya",                   12.9825, 77.7190),
    Stop("L1_S31", "Kundalahalli",                      12.9762, 77.7248),
    Stop("L1_S32", "Nallurhalli",                       12.9715, 77.7340),
    Stop("L1_S33", "Sri Sathya Sai Hospital",           12.9780, 77.7430),
    Stop("L1_S34", "Pattandur Agrahara",                12.9876, 77.7382),
    Stop("L1_S35", "Kadugodi Tree Park",                12.9856, 77.7469),
    Stop("L1_S36", "Hopefarm Channasandra",             12.9879, 77.7541),
    Stop("L1_S37", "Whitefield (Kadugodi)",             12.9951, 77.7578),
]

# --- Metro Line L2: Namma Metro Green Line (Madavara ↔ Silk Institute) ---
Metro_L2_STOPS = [
    Stop("L2_S1",  "Madavara",                          13.0645, 77.4855),
    Stop("L2_S2",  "Chikkabidarakallu",                 13.0560, 77.4920),
    Stop("L2_S3",  "Manjunathanagar",                   13.0515, 77.4960),
    Stop("L2_S4",  "Nagasandra",                        13.0480, 77.5001),
    Stop("L2_S5",  "Dasarahalli",                       13.0425, 77.5130),
    Stop("L2_S6",  "Jalahalli",                         13.0390, 77.5195),
    Stop("L2_S7",  "Peenya Industry",                   13.0363, 77.5255),
    Stop("L2_S8",  "Peenya",                            13.0329, 77.5333),
    Stop("L2_S9",  "Goraguntepalya",                    13.0284, 77.5408),
    Stop("L2_S10", "Yeshwanthpur",                      13.0232, 77.5499),
    Stop("L2_S11", "Sandal Soap Factory",               13.0147, 77.5540),
    Stop("L2_S12", "Mahalakshmi",                       13.0082, 77.5488),
    Stop("L2_S13", "Rajajinagar",                       13.0003, 77.5497),
    Stop("L2_S14", "Mahakavi Kuvempu Road",             12.9985, 77.5570),
    Stop("L2_S15", "Srirampura",                        12.9965, 77.5633),
    Stop("L2_S16", "Sampige Road (Mantri Square)",      12.9905, 77.5710),
    Stop("L2_S17", "Nadaprabhu Kempegowda (Majestic)",  12.9757, 77.5728),
    Stop("L2_S18", "Chickpet",                          12.9690, 77.5740),
    Stop("L2_S19", "Krishna Rajendra Market",           12.9614, 77.5746),
    Stop("L2_S20", "National College",                  12.9505, 77.5745),
    Stop("L2_S21", "Lalbagh",                           12.9464, 77.5801),
    Stop("L2_S22", "South End Circle",                  12.9382, 77.5801),
    Stop("L2_S23", "Jayanagar",                         12.9300, 77.5801),
    Stop("L2_S24", "Rashtreeya Vidyalaya Road",         12.9215, 77.5804),
    Stop("L2_S25", "Banashankari",                      12.9155, 77.5735),
    Stop("L2_S26", "Jayaprakash Nagar",                 12.9075, 77.5730),
    Stop("L2_S27", "Yelachenahalli",                    12.8960, 77.5702),
    Stop("L2_S28", "Konanakunte Cross",                 12.8847, 77.5529),
    Stop("L2_S29", "Doddakallasandra",                  12.8800, 77.5480),
    Stop("L2_S30", "Vajarahalli",                       12.8775, 77.5446),
    Stop("L2_S31", "Thalaghattapura",                   12.8717, 77.5388),
    Stop("L2_S32", "Silk Institute",                    12.8619, 77.5300),
]

# --- Metro Line L3: Namma Metro Yellow Line (Simulated Operations) ---
Metro_L3_STOPS = [
    Stop("L3_S1",  "Rashtreeya Vidyalaya Road",         12.9215, 77.5804),
    Stop("L3_S2",  "Ragigudda",                         12.9170, 77.5884),
    Stop("L3_S3",  "Jayadeva Hospital",                 12.9167, 77.6001),
    Stop("L3_S4",  "BTM Layout",                        12.9166, 77.6082),
    Stop("L3_S5",  "Central Silk Board",                12.9165, 77.6206),
    Stop("L3_S6",  "Bommanahalli",                      12.9085, 77.6255),
    Stop("L3_S7",  "Hongasandra",                       12.9017, 77.6321),
    Stop("L3_S8",  "Kudlu Gate",                        12.8899, 77.6393),
    Stop("L3_S9",  "Singasandra",                       12.8807, 77.6450),
    Stop("L3_S10", "Hosa Road",                         12.8708, 77.6525),
    Stop("L3_S11", "Beratena Agrahara",                 12.8590, 77.6600),
    Stop("L3_S12", "Electronic City",                   12.8465, 77.6711),
    Stop("L3_S13", "Konappana Agrahara",                12.8390, 77.6770),
    Stop("L3_S14", "Huskur Road",                       12.8300, 77.6830),
    Stop("L3_S15", "Hebbagodi",                         12.8200, 77.6880),
    Stop("L3_S16", "Bommasandra",                       12.8120, 77.6930),
]


# ─────────────────────────────────────────────────────────────────────────────
# Route Registry
# ─────────────────────────────────────────────────────────────────────────────

ROUTES: List[Route] = [
    Route(
        route_id="BUS-101",
        name="Majestic → Whitefield",
        vehicle_type="bus",
        color="#E63946",
        stops=BUS_101_STOPS,
        headway_minutes=12,
        first_departure="05:30",
        last_departure="23:30",
        avg_speed_kmh=22.0,
        bus_number="335-E",
        display_name="BMTC Volvo Vajra 335-E",
        destination_sign="ITPL / Whitefield (via Marathahalli)",
    ),
    Route(
        route_id="BUS-102",
        name="Majestic → Electronic City",
        vehicle_type="bus",
        color="#06D6A0",
        stops=BUS_102_STOPS,
        headway_minutes=10,
        first_departure="05:00",
        last_departure="23:45",
        avg_speed_kmh=24.0,
        bus_number="365",
        display_name="BMTC Hosur Road Express 365",
        destination_sign="Electronic City (via Silk Board)",
    ),
    Route(
        route_id="BUS-103",
        name="Banashankari → Hebbal",
        vehicle_type="bus",
        color="#FFD166",
        stops=BUS_103_STOPS,
        headway_minutes=15,
        first_departure="06:00",
        last_departure="22:30",
        avg_speed_kmh=20.0,
        bus_number="500-D",
        display_name="BMTC Ring Road Circular 500-D",
        destination_sign="Hebbal TTMC (via Yeshwanthpur)",
    ),
    Route(
        route_id="BUS-104",
        name="ORR-Koramangala Loop (Simulated)",
        vehicle_type="bus",
        color="#F4A261",
        stops=BUS_104_STOPS,
        headway_minutes=20,
        first_departure="06:30",
        last_departure="22:00",
        avg_speed_kmh=18.0,
        bus_number="201-G",
        display_name="BMTC Koramangala Feeder 201-G",
        destination_sign="Koramangala - Domlur Loop",
    ),
    Route(
        route_id="BUS-105",
        name="KIA Airport Express (Vayu Vajra)",
        vehicle_type="bus",
        color="#118AB2",
        stops=BUS_105_STOPS,
        headway_minutes=8,
        first_departure="04:00",
        last_departure="01:00",
        avg_speed_kmh=35.0,
        bus_number="KIA-9",
        display_name="BMTC Vayu Vajra Airport Express KIA-9",
        destination_sign="Kempegowda Int. Airport T1/T2",
    ),
    Route(
        route_id="BUS-106",
        name="IT Corridor Connector (Simulated)",
        vehicle_type="bus",
        color="#9B5DE5",
        stops=BUS_106_STOPS,
        headway_minutes=18,
        first_departure="07:00",
        last_departure="21:00",
        avg_speed_kmh=20.0,
        bus_number="MF-1",
        display_name="BMTC IT Corridor Metro Feeder MF-1",
        destination_sign="Electronic City (via ITPL & Silk Board)",
    ),
    Route(
        route_id="Metro-L1",
        name="Namma Metro Purple Line",
        vehicle_type="metro",
        color="#8338EC",
        stops=Metro_L1_STOPS,
        headway_minutes=5,
        first_departure="05:00",
        last_departure="23:30",
        avg_speed_kmh=45.0,
        bus_number="Purple Line (L1)",
        display_name="Namma Metro Purple Line",
        destination_sign="Whitefield (Kadugodi)",
    ),
    Route(
        route_id="Metro-L2",
        name="Namma Metro Green Line",
        vehicle_type="metro",
        color="#2EC4B6",
        stops=Metro_L2_STOPS,
        headway_minutes=4,
        first_departure="05:00",
        last_departure="23:30",
        avg_speed_kmh=48.0,
        bus_number="Green Line (L2)",
        display_name="Namma Metro Green Line",
        destination_sign="Silk Institute",
    ),
    Route(
        route_id="Metro-L3",
        name="Namma Metro Yellow Line (Simulated)",
        vehicle_type="metro",
        color="#FFBE0B",
        stops=Metro_L3_STOPS,
        headway_minutes=7,
        first_departure="05:00",
        last_departure="23:00",
        avg_speed_kmh=42.0,
        bus_number="Yellow Line (L3)",
        display_name="Namma Metro Yellow Line",
        destination_sign="Bommasandra (Electronic City)",
    ),
]

# Quick lookup dicts
ROUTE_BY_ID: Dict[str, Route] = {r.route_id: r for r in ROUTES}
STOP_BY_ID: Dict[str, Stop]   = {}
for _r in ROUTES:
    for _s in _r.stops:
        STOP_BY_ID[_s.stop_id] = _s
