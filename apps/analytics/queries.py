"""Every business question in the case study, answered against the star schema.

Each function returns plain Python — lists and dicts — so the views stay thin
and the templates never touch the ORM.
"""

from decimal import Decimal

from django.db.models import Avg, Count, DecimalField, Max, Min, Q, Sum, Value
from django.db.models.functions import Coalesce

from warehouse import models as dw

DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MONTH_NAMES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
ZERO = Value(Decimal("0.00"), output_field=DecimalField(max_digits=18, decimal_places=2))


class Period:
    """Rango de fechas con el que se acotan todas las consultas.

    Ambos extremos son opcionales: un ``Period()`` sin límites significa todo
    el histórico, y así se comporta igual que no pasar periodo alguno. El
    filtro se aplica sobre ``dim_date.full_date``, que está indexado.
    """

    def __init__(self, start=None, end=None):
        self.start = start
        self.end = end

    @property
    def is_open(self):
        return self.start is None and self.end is None

    def label(self):
        if self.is_open:
            return "todo el histórico"
        if self.start and self.end:
            return f"{_spell(self.start)} — {_spell(self.end)}"
        if self.start:
            return f"desde {_spell(self.start)}"
        return f"hasta {_spell(self.end)}"


def _spell(day):
    return f"{day.day} de {MONTH_NAMES[day.month - 1]} de {day.year}"


def _scope(queryset, period):
    """Acota cualquier tabla de hechos al periodo. Todas cuelgan de dim_date."""
    if period is None or period.is_open:
        return queryset
    if period.start:
        queryset = queryset.filter(date__full_date__gte=period.start)
    if period.end:
        queryset = queryset.filter(date__full_date__lte=period.end)
    return queryset


def _deliveries(period=None):
    return _scope(dw.FactDelivery.objects.all(), period)


def _fuel(period=None):
    return _scope(dw.FactFuel.objects.all(), period)


def _maintenance(period=None):
    return _scope(dw.FactMaintenance.objects.all(), period)


def warehouse_is_empty():
    return not dw.FactDelivery.objects.exists()


def data_bounds():
    """Primera y última fecha con entregas en el almacén.

    Los atajos de periodo se ancoran aquí y no en la fecha de hoy: el almacén
    puede terminar semanas atrás, y un "último mes" contado desde hoy
    devolvería una pantalla vacía.
    """
    bounds = dw.FactDelivery.objects.aggregate(
        first=Min("date__full_date"), last=Max("date__full_date")
    )
    return bounds["first"], bounds["last"]


def kpi_summary(period=None):
    """The six headline numbers, plus the two cost totals behind them."""
    deliveries = _deliveries(period).aggregate(
        total=Count("id"),
        delayed=Count("id", filter=Q(is_delayed=1)),
        avg_delay=Coalesce(Avg("delay_minutes"), 0.0),
        freight=Coalesce(Sum("freight_cost"), ZERO),
        km=Coalesce(Sum("distance_km"), ZERO),
    )
    fuel = _fuel(period).aggregate(
        cost=Coalesce(Sum("total_cost"), ZERO),
        efficiency=Avg("efficiency_km_per_liter"),
    )
    maintenance = _maintenance(period).aggregate(
        cost=Coalesce(Sum("total_cost"), ZERO)
    )

    total = deliveries["total"] or 0
    on_time = total - (deliveries["delayed"] or 0)
    return {
        "deliveries": total,
        "on_time_rate": round((on_time / total) * 100, 1) if total else 0.0,
        "avg_delay_minutes": round(float(deliveries["avg_delay"] or 0), 1),
        "total_freight": deliveries["freight"],
        "total_km": deliveries["km"],
        "avg_efficiency": round(float(fuel["efficiency"] or 0), 2),
        "fuel_cost": fuel["cost"],
        "maintenance_cost": maintenance["cost"],
    }


def monthly_trend(period=None):
    rows = (
        _deliveries(period).values("date__year", "date__month", "date__month_name")
        .annotate(
            deliveries=Count("id"),
            delayed=Count("id", filter=Q(is_delayed=1)),
            freight=Coalesce(Sum("freight_cost"), ZERO),
        )
        .order_by("date__year", "date__month")
    )
    return {
        "labels": [
            f"{row['date__month_name'][:3]} {row['date__year']}" for row in rows
        ],
        "deliveries": [row["deliveries"] for row in rows],
        "delayed": [row["delayed"] for row in rows],
        "freight": [float(row["freight"]) for row in rows],
    }


def top_routes(limit=10, period=None):
    """P1 — rutas más utilizadas, con su tasa de retraso al lado."""
    rows = (
        _deliveries(period).values(
            "route__code", "route__name", "route__zone"
        )
        .annotate(shipments=Count("id"), delayed=Count("id", filter=Q(is_delayed=1)))
        .order_by("-shipments")[:limit]
    )
    return [
        {
            "code": row["route__code"],
            "name": row["route__name"],
            "zone": row["route__zone"],
            "shipments": row["shipments"],
            "delay_rate": round(row["delayed"] / row["shipments"] * 100, 1),
        }
        for row in rows
    ]


def worst_routes(limit=10, period=None):
    """P4 — rutas con mayores retrasos (mínimo 20 envíos para que sea señal)."""
    rows = (
        _deliveries(period).values("route__code", "route__name", "route__zone")
        .annotate(
            shipments=Count("id"),
            delayed=Count("id", filter=Q(is_delayed=1)),
            avg_delay=Avg("delay_minutes"),
        )
        .filter(shipments__gte=20)
        .order_by("-avg_delay")[:limit]
    )
    return [
        {
            "code": row["route__code"],
            "name": row["route__name"],
            "zone": row["route__zone"],
            "shipments": row["shipments"],
            "delay_rate": round(row["delayed"] / row["shipments"] * 100, 1),
            "avg_delay": round(float(row["avg_delay"]), 1),
        }
        for row in rows
    ]


def top_operators(limit=10, period=None):
    """P3 — operadores con más entregas."""
    rows = (
        _deliveries(period).values(
            "operator__employee_number", "operator__full_name"
        )
        .annotate(deliveries=Count("id"), delayed=Count("id", filter=Q(is_delayed=1)))
        .order_by("-deliveries")[:limit]
    )
    return [
        {
            "employee_number": row["operator__employee_number"],
            "full_name": row["operator__full_name"],
            "deliveries": row["deliveries"],
            "delay_rate": round(row["delayed"] / row["deliveries"] * 100, 1),
        }
        for row in rows
    ]


def demand_by_service_type(period=None):
    """Demanda por tipo de servicio: qué corredor mueve más carga.

    Los tres tipos (LOCAL, REGIONAL, FORANEA) parten el total de envíos, así
    que la participación de cada uno suma cien por ciento.
    """
    rows = (
        _deliveries(period).values("route__route_type")
        .annotate(
            shipments=Count("id"),
            delayed=Count("id", filter=Q(is_delayed=1)),
            freight=Coalesce(Sum("freight_cost"), ZERO),
            routes=Count("route", distinct=True),
        )
        .order_by("-shipments")
    )
    total = sum(row["shipments"] for row in rows)
    return [
        {
            "service_type": row["route__route_type"],
            "shipments": row["shipments"],
            "share": round(row["shipments"] / total * 100, 1) if total else 0.0,
            "delay_rate": round(row["delayed"] / row["shipments"] * 100, 1),
            "freight": row["freight"],
            "routes": row["routes"],
        }
        for row in rows
    ]


def top_customers(limit=10, period=None):
    """Clientes que concentran la demanda, con el flete que aportan."""
    rows = (
        _deliveries(period).values(
            "customer__code", "customer__business_name",
            "customer__city", "customer__customer_type",
        )
        .annotate(
            shipments=Count("id"),
            delayed=Count("id", filter=Q(is_delayed=1)),
            freight=Coalesce(Sum("freight_cost"), ZERO),
        )
        .order_by("-shipments")[:limit]
    )
    return [
        {
            "code": row["customer__code"],
            "business_name": row["customer__business_name"],
            "city": row["customer__city"],
            "customer_type": row["customer__customer_type"],
            "shipments": row["shipments"],
            "delay_rate": round(row["delayed"] / row["shipments"] * 100, 1),
            "freight": row["freight"],
        }
        for row in rows
    ]


def hour_heatmap(period=None):
    """P10 — horarios de mayor saturación, día de la semana x hora."""
    matrix = [[0] * 24 for _ in range(7)]
    rows = (
        _deliveries(period).values("date__day_of_week", "time__hour")
        .annotate(total=Count("id"))
    )
    for row in rows:
        matrix[row["date__day_of_week"]][row["time__hour"]] = row["total"]
    return {"days": DAY_NAMES, "hours": list(range(24)), "matrix": matrix}


def delay_causes_pareto(period=None):
    """P6 — causas principales de retraso, ordenadas y acumuladas."""
    rows = (
        _deliveries(period).filter(delay_cause__isnull=False)
        .values("delay_cause__name")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    counts = [row["total"] for row in rows]
    grand_total = sum(counts) or 1
    cumulative, running = [], 0
    for value in counts:
        running += value
        cumulative.append(round(running / grand_total * 100, 1))
    return {
        "labels": [row["delay_cause__name"] for row in rows],
        "counts": counts,
        "cumulative": cumulative,
    }


def cost_by_vehicle(limit=15, period=None):
    """P2 — vehículos que generan mayores costos: combustible + mantenimiento."""
    fuel = {
        row["vehicle_id"]: row["total"]
        for row in _fuel(period).values("vehicle_id").annotate(
            total=Coalesce(Sum("total_cost"), ZERO)
        )
    }
    maintenance = {
        row["vehicle_id"]: row["total"]
        for row in _maintenance(period).values("vehicle_id").annotate(
            total=Coalesce(Sum("total_cost"), ZERO)
        )
    }
    rows = []
    for vehicle in dw.DimVehicle.objects.all():
        fuel_cost = fuel.get(vehicle.vehicle_key, Decimal("0.00"))
        maintenance_cost = maintenance.get(vehicle.vehicle_key, Decimal("0.00"))
        rows.append({
            "economic_number": vehicle.economic_number,
            "plate": vehicle.plate,
            "vehicle_type": vehicle.vehicle_type,
            "age_range": vehicle.age_range,
            "fuel_cost": fuel_cost,
            "maintenance_cost": maintenance_cost,
            "total_cost": fuel_cost + maintenance_cost,
        })
    return sorted(rows, key=lambda row: row["total_cost"], reverse=True)[:limit]


def efficiency_by_vehicle(limit=15, period=None):
    """P5 — vehículos que más consumen: peor rendimiento primero."""
    rows = (
        _fuel(period).filter(efficiency_km_per_liter__isnull=False)
        .values(
            "vehicle__economic_number", "vehicle__vehicle_type", "vehicle__age_range"
        )
        .annotate(
            efficiency=Avg("efficiency_km_per_liter"),
            liters=Coalesce(Sum("liters"), ZERO),
        )
        .order_by("efficiency")[:limit]
    )
    return [
        {
            "economic_number": row["vehicle__economic_number"],
            "vehicle_type": row["vehicle__vehicle_type"],
            "age_range": row["vehicle__age_range"],
            "efficiency": round(float(row["efficiency"]), 2),
            "liters": row["liters"],
        }
        for row in rows
    ]


def cost_per_km_by_route(limit=15, period=None):
    rows = (
        _deliveries(period).values("route__code", "route__name")
        .annotate(cost_per_km=Avg("cost_per_km"), shipments=Count("id"))
        .order_by("-cost_per_km")[:limit]
    )
    return [
        {
            "code": row["route__code"],
            "name": row["route__name"],
            "cost_per_km": round(float(row["cost_per_km"]), 2),
            "shipments": row["shipments"],
        }
        for row in rows
    ]
