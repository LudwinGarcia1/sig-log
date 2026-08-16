"""Feature matrices assembled from the star schema.

The single most important thing in this file is LEAKAGE_COLUMNS. Every column
listed there is knowable only *after* the truck has arrived. Feeding any of
them to the classifier would produce near-perfect accuracy and a model with no
predictive value whatsoever — the classic mistake this project is meant to
demonstrate avoiding.
"""

import pandas as pd
from django.db import connection

# Known only after the fact. Never features.
LEAKAGE_COLUMNS = frozenset({
    "actual_departure",
    "actual_arrival",
    "status",
    "delay_cause",
    "delay_cause_code",
    "actual_duration_min",
    "delay_minutes",
    "is_delayed",
})

NUMERIC_FEATURES = [
    "distance_km",
    "planned_duration_min",
    "cargo_weight_kg",
    "packages_count",
    "day_of_week",
]

CATEGORICAL_FEATURES = [
    "route_code",
    "route_type",
    "zone",
    "distance_range",
    "time_band",
    "vehicle_type",
    "vehicle_age_range",
    "operator_seniority_range",
    "customer_type",
    "is_weekend",
]

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

CLASSIFICATION_TARGET = "is_delayed"
REGRESSION_TARGET = "delay_minutes"

DELIVERY_SQL = """
SELECT
    f.folio,
    f.distance_km::float               AS distance_km,
    f.planned_duration_min             AS planned_duration_min,
    f.cargo_weight_kg::float           AS cargo_weight_kg,
    f.packages_count                   AS packages_count,
    d.day_of_week                      AS day_of_week,
    d.is_weekend::text                 AS is_weekend,
    r.code                             AS route_code,
    r.route_type                       AS route_type,
    r.zone                             AS zone,
    r.distance_range                   AS distance_range,
    t.time_band                        AS time_band,
    v.vehicle_type                     AS vehicle_type,
    v.age_range                        AS vehicle_age_range,
    o.seniority_range                  AS operator_seniority_range,
    c.customer_type                    AS customer_type,
    f.delay_minutes                    AS delay_minutes,
    f.is_delayed                       AS is_delayed
FROM dw.fact_delivery  AS f
JOIN dw.dim_date       AS d ON d.date_key       = f.date_id
JOIN dw.dim_time       AS t ON t.time_key       = f.time_id
JOIN dw.dim_route      AS r ON r.route_key      = f.route_id
JOIN dw.dim_vehicle    AS v ON v.vehicle_key    = f.vehicle_id
JOIN dw.dim_operator   AS o ON o.operator_key   = f.operator_id
JOIN dw.dim_customer   AS c ON c.customer_key   = f.customer_id
"""

ROUTE_PROFILE_SQL = """
SELECT
    r.code                                        AS route_code,
    r.name                                        AS route_name,
    r.route_type                                  AS route_type,
    r.zone                                        AS zone,
    AVG(f.distance_km)::float                     AS distance_km,
    AVG(f.actual_duration_min)::float             AS avg_duration_min,
    AVG(f.is_delayed)::float                      AS delay_rate,
    AVG(f.delay_minutes)::float                   AS avg_delay_minutes,
    AVG(f.cargo_weight_kg)::float                 AS avg_cargo_kg,
    AVG(f.cost_per_km)::float                     AS avg_cost_per_km,
    COUNT(*)::float
        / NULLIF(COUNT(DISTINCT d.year * 12 + d.month), 0) AS monthly_shipments
FROM dw.fact_delivery AS f
JOIN dw.dim_route     AS r ON r.route_key = f.route_id
JOIN dw.dim_date      AS d ON d.date_key  = f.date_id
GROUP BY r.code, r.name, r.route_type, r.zone
"""

ROUTE_PROFILE_FEATURES = [
    "distance_km",
    "avg_duration_min",
    "delay_rate",
    "avg_delay_minutes",
    "avg_cargo_kg",
    "avg_cost_per_km",
    "monthly_shipments",
]


def build_delivery_dataset():
    """One row per completed delivery, features plus both targets."""
    frame = pd.read_sql(DELIVERY_SQL, connection)
    for column in CATEGORICAL_FEATURES:
        frame[column] = frame[column].astype(str)
    return frame


def build_route_profile():
    """One row per route, aggregated operational behaviour.

    This is the matrix that PCA and K-means work on. Routes with no completed
    deliveries are absent by construction, so a route that never ran cannot
    distort a cluster centre.
    """
    frame = pd.read_sql(ROUTE_PROFILE_SQL, connection)
    frame = frame.set_index("route_code")
    frame[ROUTE_PROFILE_FEATURES] = frame[ROUTE_PROFILE_FEATURES].fillna(0.0)
    return frame
