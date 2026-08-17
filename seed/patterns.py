"""The patterns deliberately planted in the synthetic data.

Every rule here is something the mining models in Tasks 14-16 are expected to
rediscover. Congestion is attached to ZONE rather than to individual route
identities so that it is learnable from the feature set, and route identity is
additionally exposed as a categorical feature.

The coefficients in ``delay_probability`` were tuned so the seeded pattern is
strong enough to be learnable above the F1 >= 0.75 threshold required of the
Task 14 classifier: congested-zone deliveries average roughly 0.68 probability
of being late, clean-zone deliveries roughly 0.08, and with about two thirds
of deliveries running through congested zones the expected overall delay rate
lands near 0.48 — comfortably inside the (0.10, 0.50) band asserted by
``test_delay_rate_is_realistic`` but close enough to the congested-zone rate
that a classifier using zone/route_code as a feature can separate the two
populations cleanly.
"""

from decimal import Decimal

CONGESTED_ZONES = {"METROPOLITANA", "ORIENTE"}
PEAK_HOURS = {7, 8, 9, 17, 18, 19}

# Base fuel efficiency in km per litre, before the age penalty.
BASE_EFFICIENCY = {
    "TRUCK": Decimal("2.90"),
    "TRAILER": Decimal("2.20"),
    "VAN": Decimal("6.40"),
    "PICKUP": Decimal("8.10"),
}

# Three archetypes, chosen so the route profile separates into clean clusters.
ROUTE_ARCHETYPES = [
    {
        "name": "URBANA",
        "route_type": "LOCAL",
        "zones": ["METROPOLITANA", "ORIENTE"],
        "count": 24,
        "distance_km": (12, 45),
        "speed_kmh": (22, 32),
        "monthly_volume": (28, 55),
        "cargo_kg": (400, 2500),
    },
    {
        "name": "REGIONAL",
        "route_type": "REGIONAL",
        "zones": ["CENTRO", "BAJIO", "OCCIDENTE"],
        "count": 22,
        "distance_km": (90, 280),
        "speed_kmh": (52, 68),
        "monthly_volume": (12, 26),
        "cargo_kg": (2000, 8000),
    },
    {
        "name": "FORANEA",
        "route_type": "FORANEA",
        "zones": ["NORTE", "SUR", "GOLFO"],
        "count": 14,
        "distance_km": (420, 900),
        "speed_kmh": (68, 82),
        "monthly_volume": (3, 9),
        "cargo_kg": (6000, 14000),
    },
]

DELAY_CAUSE_WEIGHTS = [
    ("TRAFICO", 34),
    ("CARGA_DESCARGA", 21),
    ("CLIMA", 14),
    ("DOCUMENTACION", 12),
    ("FALLA_MECANICA", 10),
    ("ACCIDENTE", 5),
    ("OTRO", 4),
]


def delay_probability(zone, route_type, hour, weekday, vehicle_age):
    """Probability that a delivery arrives late, given pre-departure facts.

    Every argument is knowable before the truck leaves, which is exactly the
    information the classifier is allowed to use.
    """
    probability = 0.03
    if zone in CONGESTED_ZONES:
        probability += 0.52
    if hour in PEAK_HOURS:
        probability += 0.08
    if vehicle_age > 8:
        probability += 0.07
    elif vehicle_age > 3:
        probability += 0.03
    if route_type == "LOCAL":
        probability += 0.04
    elif route_type == "FORANEA":
        probability -= 0.02
    if weekday >= 5:
        probability -= 0.05
    return min(max(probability, 0.02), 0.88)
