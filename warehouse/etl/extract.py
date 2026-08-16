"""Phase 1 — land the source tables verbatim into ``staging``.

Two extraction types, which is what Unidad II asks for:

* full        — truncate the landing zone and pull the whole history
* incremental — pull only rows whose ``updated_at`` is newer than the
                watermark of the last successful run

Nothing is cleaned here. A landing zone that edits its input cannot be used to
prove what the source actually contained.
"""

from apps.customers.models import Customer
from apps.deliveries.models import DelayCause, Delivery
from apps.fuel.models import FuelLoad
from apps.maintenance.models import Maintenance
from apps.operators.models import Operator
from apps.routes.models import Route
from apps.vehicles.models import Vehicle
from warehouse import models as dw

BATCH_SIZE = 2000


def _customer_row(source, run_id):
    return dw.StgCustomer(
        run_id=run_id, source_id=source.id, code=source.code,
        business_name=source.business_name, tax_id=source.tax_id,
        city=source.city, state=source.state,
        customer_type=source.customer_type, is_active=source.is_active,
    )


def _vehicle_row(source, run_id):
    return dw.StgVehicle(
        run_id=run_id, source_id=source.id, plate=source.plate,
        economic_number=source.economic_number, brand=source.brand,
        model=source.model, year=source.year, vehicle_type=source.vehicle_type,
        cargo_capacity_kg=source.cargo_capacity_kg, fuel_type=source.fuel_type,
        is_active=source.is_active,
    )


def _operator_row(source, run_id):
    return dw.StgOperator(
        run_id=run_id, source_id=source.id,
        employee_number=source.employee_number, first_name=source.first_name,
        last_name=source.last_name, license_type=source.license_type,
        hire_date=source.hire_date, is_active=source.is_active,
    )


def _route_row(source, run_id):
    return dw.StgRoute(
        run_id=run_id, source_id=source.id, code=source.code, name=source.name,
        origin_city=source.origin_city, destination_city=source.destination_city,
        distance_km=source.distance_km,
        estimated_duration_min=source.estimated_duration_min,
        route_type=source.route_type, zone=source.zone, is_active=source.is_active,
    )


def _delay_cause_row(source, run_id):
    return dw.StgDelayCause(
        run_id=run_id, source_id=source.id, code=source.code, name=source.name,
        category=source.category, is_active=source.is_active,
    )


def _delivery_row(source, run_id):
    return dw.StgDelivery(
        run_id=run_id, source_id=source.id, folio=source.folio,
        customer_code=source.customer.code, route_code=source.route.code,
        vehicle_plate=source.vehicle.plate,
        operator_number=source.operator.employee_number,
        delay_cause_code=source.delay_cause.code if source.delay_cause else None,
        scheduled_departure=source.scheduled_departure,
        actual_departure=source.actual_departure,
        scheduled_arrival=source.scheduled_arrival,
        actual_arrival=source.actual_arrival,
        cargo_weight_kg=source.cargo_weight_kg,
        packages_count=source.packages_count,
        declared_value=source.declared_value, freight_cost=source.freight_cost,
        status=source.status, is_active=source.is_active,
    )


def _fuel_row(source, run_id):
    return dw.StgFuelLoad(
        run_id=run_id, source_id=source.id, folio=source.folio,
        vehicle_plate=source.vehicle.plate,
        operator_number=source.operator.employee_number,
        load_datetime=source.load_datetime, liters=source.liters,
        price_per_liter=source.price_per_liter, total_cost=source.total_cost,
        odometer_km=source.odometer_km, is_active=source.is_active,
    )


def _maintenance_row(source, run_id):
    return dw.StgMaintenance(
        run_id=run_id, source_id=source.id, folio=source.folio,
        vehicle_plate=source.vehicle.plate,
        maintenance_type=source.maintenance_type, service_date=source.service_date,
        odometer_km=source.odometer_km, labor_cost=source.labor_cost,
        parts_cost=source.parts_cost, total_cost=source.total_cost,
        days_out_of_service=source.days_out_of_service, status=source.status,
        is_active=source.is_active,
    )


SOURCES = [
    ("stg_customer", Customer, dw.StgCustomer, _customer_row, ()),
    ("stg_vehicle", Vehicle, dw.StgVehicle, _vehicle_row, ()),
    ("stg_operator", Operator, dw.StgOperator, _operator_row, ()),
    ("stg_route", Route, dw.StgRoute, _route_row, ()),
    ("stg_delay_cause", DelayCause, dw.StgDelayCause, _delay_cause_row, ()),
    (
        "stg_delivery", Delivery, dw.StgDelivery, _delivery_row,
        ("customer", "route", "vehicle", "operator", "delay_cause"),
    ),
    ("stg_fuel_load", FuelLoad, dw.StgFuelLoad, _fuel_row, ("vehicle", "operator")),
    (
        "stg_maintenance", Maintenance, dw.StgMaintenance, _maintenance_row,
        ("vehicle",),
    ),
]


def run(etl_run):
    """Land every source table. Returns rows written per staging table."""
    counts = {}
    for table_name, source_model, staging_model, mapper, related in SOURCES:
        with etl_run.phase("EXTRACT", table_name) as counter:
            if etl_run.full:
                staging_model.objects.all().delete()

            queryset = source_model.objects.all()
            if related:
                queryset = queryset.select_related(*related)
            if not etl_run.full and etl_run.since is not None:
                queryset = queryset.filter(updated_at__gt=etl_run.since)

            rows = [mapper(source, etl_run.run_id) for source in queryset.iterator()]
            counter.read = len(rows)
            staging_model.objects.bulk_create(rows, batch_size=BATCH_SIZE)
            counter.written = len(rows)
            counts[table_name] = len(rows)

    return counts
