"""Fuel consumption analysis over the operational tables."""

from decimal import Decimal

from django.db.models import Count, Max, Min, Sum

from apps.fuel.models import FuelLoad


def efficiency_report(start=None, end=None):
    """Fuel usage per vehicle, worst efficiency first.

    Kilometres are measured as the odometer span between the first and last
    load in the window, which is the only honest way to attribute distance to
    fuel actually burned.
    """
    loads = FuelLoad.objects.filter(is_active=True)
    if start is not None:
        loads = loads.filter(load_datetime__gte=start)
    if end is not None:
        loads = loads.filter(load_datetime__lte=end)

    aggregated = (
        loads.values("vehicle")
        .annotate(
            loads=Count("id"),
            liters=Sum("liters"),
            cost=Sum("total_cost"),
            first_odometer=Min("odometer_km"),
            last_odometer=Max("odometer_km"),
        )
        .order_by()
    )

    from apps.vehicles.models import Vehicle

    vehicles = Vehicle.objects.in_bulk([row["vehicle"] for row in aggregated])

    rows = []
    for row in aggregated:
        vehicle_id = row["vehicle"]
        kilometres = row["last_odometer"] - row["first_odometer"]
        litres = row["liters"] or Decimal("0.00")

        # The earliest load in the window produced no measured distance — it
        # is the fill that got the vehicle to the first odometer reading, not
        # fuel burned within the window. Exclude it so efficiency reflects
        # fuel actually burned to cover the measured span.
        earliest_load = (
            loads.filter(vehicle_id=vehicle_id).order_by("load_datetime").first()
        )
        earliest_liters = earliest_load.liters if earliest_load else Decimal("0.00")
        consumed_liters = litres - earliest_liters

        efficiency = (
            (kilometres / consumed_liters).quantize(Decimal("0.01"))
            if kilometres > 0 and consumed_liters > 0
            else None
        )
        rows.append(
            {
                "vehicle": vehicles[vehicle_id],
                "loads": row["loads"],
                "liters": litres,
                "cost": row["cost"] or Decimal("0.00"),
                "km": kilometres,
                "efficiency": efficiency,
            }
        )

    return sorted(
        rows,
        key=lambda item: (item["efficiency"] is not None, item["efficiency"] or 0),
    )
