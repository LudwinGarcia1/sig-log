"""Phase 2 — turn landed rows into clean, typed, derived records.

Every rejection is written to ``dw.etl_error`` with the name of the rule that
caused it. Nothing is discarded in silence.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from warehouse import models as dw
from warehouse.etl import cleaning

REFERENCE_YEAR = date.today().year
DELAY_TOLERANCE_MINUTES = 15


def _payload(row, *fields):
    """A JSON-safe snapshot of the offending row, for the error log."""
    snapshot = {}
    for field in fields:
        value = getattr(row, field, None)
        snapshot[field] = None if value is None else str(value)
    return snapshot


def _minutes(start, end):
    return int(round((end - start).total_seconds() / 60))


def _transform_customers(etl_run):
    seen, clean = set(), []
    with etl_run.phase("TRANSFORM", "stg_customer") as counter:
        rows = dw.StgCustomer.objects.order_by("-extracted_at", "-id")
        counter.read = rows.count()
        for row in rows:
            code = cleaning.normalize_code(row.code)
            if not code:
                counter.rejected += 1
                etl_run.reject("stg_customer", row.source_id, "normalize_code",
                               "Código de cliente vacío.",
                               _payload(row, "code", "business_name"))
                continue
            if code in seen:                       # deduplicate, newest wins
                counter.rejected += 1
                etl_run.reject("stg_customer", code, "deduplicate",
                               "Clave natural repetida; se conserva el registro más reciente.",
                               _payload(row, "code", "business_name"))
                continue
            seen.add(code)
            clean.append({
                "code": code,
                "business_name": cleaning.normalize_text(row.business_name),
                "tax_id": cleaning.normalize_code(row.tax_id),
                "city": cleaning.default_if_blank(
                    cleaning.normalize_text(row.city), cleaning.UNKNOWN_TEXT
                ),
                "state": cleaning.default_if_blank(
                    cleaning.normalize_text(row.state), cleaning.UNKNOWN_TEXT
                ),
                "customer_type": cleaning.normalize_code(row.customer_type) or "REGULAR",
            })
        counter.written = len(clean)
    return clean


def _transform_vehicles(etl_run):
    seen, clean = set(), []
    with etl_run.phase("TRANSFORM", "stg_vehicle") as counter:
        rows = dw.StgVehicle.objects.order_by("-extracted_at", "-id")
        counter.read = rows.count()
        for row in rows:
            plate = cleaning.normalize_plate(row.plate)
            if not plate or plate in seen:
                counter.rejected += 1
                etl_run.reject("stg_vehicle", row.plate, "deduplicate",
                               "Placa vacía o repetida.", _payload(row, "plate"))
                continue
            seen.add(plate)
            clean.append({
                "plate": plate,
                "economic_number": cleaning.normalize_code(row.economic_number),
                "brand": cleaning.normalize_text(row.brand),
                "model": cleaning.normalize_text(row.model),
                "year": int(row.year),
                "vehicle_type": cleaning.normalize_code(row.vehicle_type),
                "age_range": cleaning.age_range(row.year, REFERENCE_YEAR),
                "capacity_range": cleaning.capacity_range(row.cargo_capacity_kg),
            })
        counter.written = len(clean)
    return clean


def _transform_operators(etl_run):
    seen, clean = set(), []
    with etl_run.phase("TRANSFORM", "stg_operator") as counter:
        rows = dw.StgOperator.objects.order_by("-extracted_at", "-id")
        counter.read = rows.count()
        today = date.today()
        for row in rows:
            number = cleaning.normalize_code(row.employee_number)
            if not number or number in seen:
                counter.rejected += 1
                etl_run.reject("stg_operator", row.employee_number, "deduplicate",
                               "Número de empleado vacío o repetido.",
                               _payload(row, "employee_number"))
                continue
            seen.add(number)
            clean.append({
                "employee_number": number,
                "full_name": cleaning.normalize_text(
                    f"{row.first_name or ''} {row.last_name or ''}"
                ),
                "license_type": cleaning.normalize_code(row.license_type) or "C",
                "seniority_range": cleaning.seniority_range(row.hire_date, today),
            })
        counter.written = len(clean)
    return clean


def _transform_routes(etl_run):
    seen, clean = set(), []
    with etl_run.phase("TRANSFORM", "stg_route") as counter:
        rows = dw.StgRoute.objects.order_by("-extracted_at", "-id")
        counter.read = rows.count()
        for row in rows:
            code = cleaning.normalize_code(row.code)
            if not code or code in seen:
                counter.rejected += 1
                etl_run.reject("stg_route", row.code, "deduplicate",
                               "Código de ruta vacío o repetido.", _payload(row, "code"))
                continue
            if not cleaning.is_positive(row.distance_km):
                counter.rejected += 1
                etl_run.reject("stg_route", code, "is_positive",
                               "La distancia debe ser mayor que cero.",
                               _payload(row, "code", "distance_km"))
                continue
            seen.add(code)
            clean.append({
                "code": code,
                "name": cleaning.normalize_text(row.name),
                "origin_city": cleaning.default_if_blank(
                    cleaning.normalize_text(row.origin_city)
                ),
                "destination_city": cleaning.default_if_blank(
                    cleaning.normalize_text(row.destination_city)
                ),
                "distance_km": row.distance_km,
                "distance_range": cleaning.distance_range(row.distance_km),
                "route_type": cleaning.normalize_code(row.route_type),
                "zone": cleaning.default_if_blank(
                    cleaning.normalize_code(row.zone), "SIN_ZONA"
                ),
            })
        counter.written = len(clean)
    return clean


def _transform_delay_causes(etl_run):
    seen, clean = set(), []
    with etl_run.phase("TRANSFORM", "stg_delay_cause") as counter:
        rows = dw.StgDelayCause.objects.order_by("-extracted_at", "-id")
        counter.read = rows.count()
        for row in rows:
            code = cleaning.normalize_code(row.code)
            if not code or code in seen:
                counter.rejected += 1
                etl_run.reject("stg_delay_cause", code, "deduplicate",
                               "Clave natural repetida; se conserva el registro más reciente.",
                               _payload(row, "code", "name"))
                continue
            seen.add(code)
            clean.append({
                "code": code,
                "name": cleaning.normalize_text(row.name),
                "category": cleaning.normalize_code(row.category) or "EXTERNA",
            })
        # The unspecified marker must always exist for late rows with no cause.
        if cleaning.UNSPECIFIED_CAUSE not in seen:
            clean.append({
                "code": cleaning.UNSPECIFIED_CAUSE,
                "name": "No Especificada",
                "category": "EXTERNA",
            })
        counter.written = len(clean)
    return clean


def _transform_deliveries(etl_run, valid_customers, valid_routes,
                          valid_vehicles, valid_operators, valid_causes):
    seen, clean = set(), []
    with etl_run.phase("TRANSFORM", "stg_delivery") as counter:
        rows = dw.StgDelivery.objects.order_by("-extracted_at", "-id")
        counter.read = rows.count()
        for row in rows:
            folio = cleaning.normalize_code(row.folio)
            fields = ("folio", "customer_code", "route_code", "vehicle_plate",
                      "operator_number", "scheduled_arrival", "actual_arrival",
                      "actual_departure", "freight_cost")

            if not folio or folio in seen:
                counter.rejected += 1
                etl_run.reject("stg_delivery", folio, "deduplicate",
                               "Folio vacío o repetido.", _payload(row, *fields))
                continue

            # Value-sanity checks apply regardless of delivery status: a
            # negative freight cost is a defect whether the trip is closed
            # or still open, so it is checked before the open-delivery
            # exclusion below.
            if not cleaning.is_non_negative(row.freight_cost):
                counter.rejected += 1
                etl_run.reject("stg_delivery", folio, "is_non_negative",
                               "El flete no puede ser negativo.",
                               _payload(row, *fields))
                continue

            # Only closed deliveries belong in the fact table.
            if row.actual_arrival is None:
                counter.rejected += 1
                etl_run.reject("stg_delivery", folio, "open_delivery",
                               "Entrega sin llegada real; no forma parte del hecho.",
                               _payload(row, *fields))
                continue

            departure = row.actual_departure or row.scheduled_departure
            if not cleaning.dates_are_coherent(departure, row.actual_arrival):
                counter.rejected += 1
                etl_run.reject("stg_delivery", folio, "dates_are_coherent",
                               "La llegada real es anterior a la salida.",
                               _payload(row, *fields))
                continue

            customer = cleaning.normalize_code(row.customer_code)
            route = cleaning.normalize_code(row.route_code)
            plate = cleaning.normalize_plate(row.vehicle_plate)
            operator = cleaning.normalize_code(row.operator_number)
            missing = [
                name for name, value, universe in (
                    ("cliente", customer, valid_customers),
                    ("ruta", route, valid_routes),
                    ("vehículo", plate, valid_vehicles),
                    ("operador", operator, valid_operators),
                )
                if value not in universe
            ]
            if missing:
                counter.rejected += 1
                etl_run.reject("stg_delivery", folio, "referential_integrity",
                               f"Referencia inexistente: {', '.join(missing)}.",
                               _payload(row, *fields))
                continue

            seen.add(folio)
            delay = max(_minutes(row.scheduled_arrival, row.actual_arrival), 0)
            is_delayed = 1 if delay > DELAY_TOLERANCE_MINUTES else 0
            cause = cleaning.normalize_code(row.delay_cause_code)
            if is_delayed and cause not in valid_causes:
                cause = cleaning.UNSPECIFIED_CAUSE
            if not is_delayed:
                cause = None

            planned = _minutes(row.scheduled_departure, row.scheduled_arrival)
            actual = _minutes(departure, row.actual_arrival)
            distance = valid_routes[route]
            try:
                cost_per_km = (Decimal(row.freight_cost) / distance).quantize(
                    Decimal("0.0001")
                )
            except (InvalidOperation, ZeroDivisionError):
                cost_per_km = Decimal("0.0000")

            local_departure = row.scheduled_departure.astimezone()
            clean.append({
                "folio": folio,
                "customer_code": customer,
                "route_code": route,
                "vehicle_plate": plate,
                "operator_number": operator,
                "delay_cause_code": cause,
                "date_key": int(local_departure.strftime("%Y%m%d")),
                "time_key": local_departure.hour,
                "cargo_weight_kg": row.cargo_weight_kg,
                "packages_count": row.packages_count or 0,
                "freight_cost": row.freight_cost,
                "planned_duration_min": planned,
                "actual_duration_min": actual,
                "delay_minutes": delay,
                "is_delayed": is_delayed,
                "distance_km": distance,
                "cost_per_km": cost_per_km,
            })
        counter.written = len(clean)
    return clean


def _transform_fuel_loads(etl_run, valid_vehicles, valid_operators):
    seen, clean = set(), []
    previous_odometer = {}
    with etl_run.phase("TRANSFORM", "stg_fuel_load") as counter:
        rows = dw.StgFuelLoad.objects.order_by("vehicle_plate", "load_datetime")
        counter.read = rows.count()
        for row in rows:
            folio = cleaning.normalize_code(row.folio)
            plate = cleaning.normalize_plate(row.vehicle_plate)
            operator = cleaning.normalize_code(row.operator_number)
            fields = ("folio", "vehicle_plate", "liters", "odometer_km")

            # The odometer chain is bookkeeping about the VEHICLE, not about
            # this row. A row can be rejected for its own reasons and still
            # be evidence that the vehicle passed that kilometre, so the
            # chain advances regardless of what happens to this row below.
            last = previous_odometer.get(plate)
            travelled = (
                None
                if last is None or row.odometer_km is None
                else row.odometer_km - last
            )
            if plate and row.odometer_km is not None:
                previous_odometer[plate] = row.odometer_km

            if not folio or folio in seen:
                counter.rejected += 1
                etl_run.reject("stg_fuel_load", folio, "deduplicate",
                               "Folio vacío o repetido.", _payload(row, *fields))
                continue
            if not cleaning.is_positive(row.liters):
                counter.rejected += 1
                etl_run.reject("stg_fuel_load", folio, "is_positive",
                               "Los litros deben ser mayores que cero.",
                               _payload(row, *fields))
                continue
            if plate not in valid_vehicles or operator not in valid_operators:
                counter.rejected += 1
                etl_run.reject("stg_fuel_load", folio, "referential_integrity",
                               "Vehículo u operador inexistente.",
                               _payload(row, *fields))
                continue

            efficiency = None
            if travelled is not None and travelled > 0 and row.liters:
                efficiency = (travelled / row.liters).quantize(Decimal("0.01"))

            if cleaning.is_efficiency_outlier(efficiency):
                counter.rejected += 1
                etl_run.reject("stg_fuel_load", folio, "is_efficiency_outlier",
                               f"Rendimiento fuera del rango "
                               f"{cleaning.EFFICIENCY_BOUNDS}: {efficiency} km/L.",
                               _payload(row, *fields))
                continue

            seen.add(folio)
            local_moment = row.load_datetime.astimezone()
            clean.append({
                "folio": folio,
                "vehicle_plate": plate,
                "operator_number": operator,
                "date_key": int(local_moment.strftime("%Y%m%d")),
                "time_key": local_moment.hour,
                "liters": row.liters,
                "price_per_liter": row.price_per_liter,
                "total_cost": row.total_cost,
                "km_traveled": travelled,
                "efficiency_km_per_liter": efficiency,
            })
        counter.written = len(clean)
    return clean


def _transform_maintenances(etl_run, valid_vehicles):
    seen, clean = set(), []
    with etl_run.phase("TRANSFORM", "stg_maintenance") as counter:
        rows = dw.StgMaintenance.objects.order_by("-extracted_at", "-id")
        counter.read = rows.count()
        for row in rows:
            folio = cleaning.normalize_code(row.folio)
            plate = cleaning.normalize_plate(row.vehicle_plate)
            fields = ("folio", "vehicle_plate", "total_cost", "service_date")

            if not folio or folio in seen:
                counter.rejected += 1
                etl_run.reject("stg_maintenance", folio, "deduplicate",
                               "Folio vacío o repetido.", _payload(row, *fields))
                continue
            if plate not in valid_vehicles:
                counter.rejected += 1
                etl_run.reject("stg_maintenance", folio, "referential_integrity",
                               "Vehículo inexistente.", _payload(row, *fields))
                continue
            if not cleaning.is_non_negative(row.total_cost):
                counter.rejected += 1
                etl_run.reject("stg_maintenance", folio, "is_non_negative",
                               "El costo total no puede ser negativo.",
                               _payload(row, *fields))
                continue

            seen.add(folio)
            clean.append({
                "folio": folio,
                "vehicle_plate": plate,
                "date_key": int(row.service_date.strftime("%Y%m%d")),
                "maintenance_type": cleaning.normalize_code(row.maintenance_type),
                "labor_cost": row.labor_cost,
                "parts_cost": row.parts_cost,
                "total_cost": row.total_cost,
                "days_out_of_service": row.days_out_of_service or 0,
                "odometer_km": row.odometer_km,
            })
        counter.written = len(clean)
    return clean


def run(etl_run):
    """Clean every landed table and return records ready for Load."""
    customers = _transform_customers(etl_run)
    vehicles = _transform_vehicles(etl_run)
    operators = _transform_operators(etl_run)
    routes = _transform_routes(etl_run)
    delay_causes = _transform_delay_causes(etl_run)

    customer_codes = {row["code"] for row in customers}
    vehicle_plates = {row["plate"] for row in vehicles}
    operator_numbers = {row["employee_number"] for row in operators}
    cause_codes = {row["code"] for row in delay_causes}
    route_distances = {row["code"]: row["distance_km"] for row in routes}

    return {
        "customers": customers,
        "vehicles": vehicles,
        "operators": operators,
        "routes": routes,
        "delay_causes": delay_causes,
        "deliveries": _transform_deliveries(
            etl_run, customer_codes, route_distances,
            vehicle_plates, operator_numbers, cause_codes,
        ),
        "fuel_loads": _transform_fuel_loads(
            etl_run, vehicle_plates, operator_numbers
        ),
        "maintenances": _transform_maintenances(etl_run, vehicle_plates),
    }
