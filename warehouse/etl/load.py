"""Phase 3 — upsert dimensions, then bulk-load the facts.

Dimensions use SCD type 1: the natural key is matched and attributes are
overwritten. Type 2 would need validity windows and versioning that this scope
does not justify; the choice is deliberate and documented.
"""

from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from warehouse import models as dw
from warehouse.etl.calendar import build_date_dimension, build_time_dimension

BATCH_SIZE = 2000

DIMENSION_SPECS = [
    ("dim_customer", dw.DimCustomer, "code", "customers",
     ["business_name", "city", "state", "customer_type"]),
    ("dim_vehicle", dw.DimVehicle, "plate", "vehicles",
     ["economic_number", "brand", "model", "year", "vehicle_type",
      "age_range", "capacity_range"]),
    ("dim_operator", dw.DimOperator, "employee_number", "operators",
     ["full_name", "license_type", "seniority_range"]),
    ("dim_route", dw.DimRoute, "code", "routes",
     ["name", "origin_city", "destination_city", "distance_km",
      "distance_range", "route_type", "zone"]),
    ("dim_delay_cause", dw.DimDelayCause, "code", "delay_causes",
     ["name", "category"]),
]


def _load_dimension(etl_run, table_name, model, natural_key, records, attributes):
    """SCD type 1 upsert keyed on the natural key."""
    with etl_run.phase("LOAD", table_name) as counter:
        counter.read = len(records)
        existing = {
            getattr(instance, natural_key): instance
            for instance in model.objects.all()
        }
        to_create, to_update = [], []
        for record in records:
            key = record[natural_key]
            instance = existing.get(key)
            if instance is None:
                kwargs = {natural_key: key}
                kwargs.update({attribute: record[attribute] for attribute in attributes})
                to_create.append(model(**kwargs))
            else:
                for attribute in attributes:
                    setattr(instance, attribute, record[attribute])
                to_update.append(instance)
        model.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
        if to_update:
            model.objects.bulk_update(to_update, attributes, batch_size=BATCH_SIZE)
        counter.written = len(to_create) + len(to_update)
    return model.objects.count()


def _key_maps():
    return {
        "customer": dict(dw.DimCustomer.objects.values_list("code", "customer_key")),
        "vehicle": dict(dw.DimVehicle.objects.values_list("plate", "vehicle_key")),
        "operator": dict(
            dw.DimOperator.objects.values_list("employee_number", "operator_key")
        ),
        "route": dict(dw.DimRoute.objects.values_list("code", "route_key")),
        "cause": dict(
            dw.DimDelayCause.objects.values_list("code", "delay_cause_key")
        ),
    }


def _calendar_bounds(transformed):
    keys = [
        record["date_key"]
        for group in ("deliveries", "fuel_loads", "maintenances")
        for record in transformed.get(group, [])
    ]
    if not keys:
        today = date.today()
        return today - timedelta(days=1), today
    def to_date(key):
        text = str(key)
        return date(int(text[:4]), int(text[4:6]), int(text[6:]))
    return to_date(min(keys)), to_date(max(keys))


def run(etl_run, transformed):
    """Load the whole warehouse.

    The heavy lifting happens inside a single transaction (``_load_all``):
    never a half-built DW. If it fails, the transaction rolls back — including
    every per-table SUCCESS row that ``EtlRun.phase()`` wrote along the way,
    since those rows would otherwise describe work that no longer exists. What
    survives is a single FAILED row recorded here, after the rollback, so the
    operator is never left with no trace of the run at all.
    """
    started = timezone.now()
    try:
        with transaction.atomic():
            return _load_all(etl_run, transformed)
    except Exception as error:
        dw.EtlLog.objects.create(
            run_id=etl_run.run_id,
            phase="LOAD",
            table_name="(fase completa)",
            started_at=started,
            finished_at=timezone.now(),
            status="FAILED",
            message=f"{type(error).__name__}: {error}",
        )
        raise


def _load_all(etl_run, transformed):
    """Body of the LOAD phase, run inside the caller's transaction."""
    counts = {}

    if etl_run.rebuild:
        dw.FactDelivery.objects.all().delete()
        dw.FactFuel.objects.all().delete()
        dw.FactMaintenance.objects.all().delete()
        dw.DimDelayCause.objects.all().delete()
        dw.DimRoute.objects.all().delete()
        dw.DimOperator.objects.all().delete()
        dw.DimVehicle.objects.all().delete()
        dw.DimCustomer.objects.all().delete()

    for table_name, model, natural_key, group, attributes in DIMENSION_SPECS:
        counts[table_name] = _load_dimension(
            etl_run, table_name, model, natural_key,
            transformed.get(group, []), attributes,
        )

    with etl_run.phase("LOAD", "dim_time") as counter:
        counter.written = build_time_dimension()
        counts["dim_time"] = counter.written

    with etl_run.phase("LOAD", "dim_date") as counter:
        start, end = _calendar_bounds(transformed)
        counter.written = build_date_dimension(start, end)
        counts["dim_date"] = counter.written

    keys = _key_maps()

    with etl_run.phase("LOAD", "fact_delivery") as counter:
        records = transformed.get("deliveries", [])
        counter.read = len(records)
        known = set(dw.FactDelivery.objects.values_list("folio", flat=True))
        rows = [
            dw.FactDelivery(
                folio=record["folio"],
                date_id=record["date_key"],
                time_id=record["time_key"],
                customer_id=keys["customer"][record["customer_code"]],
                route_id=keys["route"][record["route_code"]],
                vehicle_id=keys["vehicle"][record["vehicle_plate"]],
                operator_id=keys["operator"][record["operator_number"]],
                delay_cause_id=(
                    keys["cause"][record["delay_cause_code"]]
                    if record["delay_cause_code"] else None
                ),
                cargo_weight_kg=record["cargo_weight_kg"],
                packages_count=record["packages_count"],
                freight_cost=record["freight_cost"],
                planned_duration_min=record["planned_duration_min"],
                actual_duration_min=record["actual_duration_min"],
                delay_minutes=record["delay_minutes"],
                is_delayed=record["is_delayed"],
                distance_km=record["distance_km"],
                cost_per_km=record["cost_per_km"],
            )
            for record in records
            if record["folio"] not in known
        ]
        dw.FactDelivery.objects.bulk_create(rows, batch_size=BATCH_SIZE)
        counter.written = len(rows)
        counts["fact_delivery"] = dw.FactDelivery.objects.count()

    with etl_run.phase("LOAD", "fact_fuel") as counter:
        records = transformed.get("fuel_loads", [])
        counter.read = len(records)
        known = set(dw.FactFuel.objects.values_list("folio", flat=True))
        rows = [
            dw.FactFuel(
                folio=record["folio"],
                date_id=record["date_key"],
                time_id=record["time_key"],
                vehicle_id=keys["vehicle"][record["vehicle_plate"]],
                operator_id=keys["operator"][record["operator_number"]],
                liters=record["liters"],
                price_per_liter=record["price_per_liter"],
                total_cost=record["total_cost"],
                km_traveled=record["km_traveled"],
                efficiency_km_per_liter=record["efficiency_km_per_liter"],
            )
            for record in records
            if record["folio"] not in known
        ]
        dw.FactFuel.objects.bulk_create(rows, batch_size=BATCH_SIZE)
        counter.written = len(rows)
        counts["fact_fuel"] = dw.FactFuel.objects.count()

    with etl_run.phase("LOAD", "fact_maintenance") as counter:
        records = transformed.get("maintenances", [])
        counter.read = len(records)
        known = set(dw.FactMaintenance.objects.values_list("folio", flat=True))
        rows = [
            dw.FactMaintenance(
                folio=record["folio"],
                date_id=record["date_key"],
                vehicle_id=keys["vehicle"][record["vehicle_plate"]],
                maintenance_type=record["maintenance_type"],
                labor_cost=record["labor_cost"],
                parts_cost=record["parts_cost"],
                total_cost=record["total_cost"],
                days_out_of_service=record["days_out_of_service"],
                odometer_km=record["odometer_km"],
            )
            for record in records
            if record["folio"] not in known
        ]
        dw.FactMaintenance.objects.bulk_create(rows, batch_size=BATCH_SIZE)
        counter.written = len(rows)
        counts["fact_maintenance"] = dw.FactMaintenance.objects.count()

    return counts
