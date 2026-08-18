"""Operational rules about fleet health.

These read the OLTP, not the warehouse: "which vehicle needs service today?"
is an operational question, and the warehouse is refreshed in batches.
"""

from decimal import Decimal

from apps.vehicles.models import SERVICE_MAX_DAYS, SERVICE_WARNING_KM, Vehicle


def maintenance_alerts():
    """Vehicles that require service, ordered by urgency.

    Returns one dictionary per vehicle with a human-readable Spanish reason
    so the analytics view can render it without re-deriving the rule.
    """
    alerts = []
    candidates = Vehicle.objects.filter(is_active=True).exclude(
        status="OUT_OF_SERVICE"
    )
    for vehicle in candidates:
        remaining = vehicle.km_to_next_service
        elapsed = vehicle.days_since_service

        if remaining <= Decimal("0.00"):
            reason = (
                f"Kilometraje vencido por {abs(remaining):.0f} km "
                f"respecto al próximo servicio."
            )
            severity = "ALTA"
        elif elapsed is None:
            reason = "Sin registro de servicio previo."
            severity = "ALTA"
        elif elapsed > SERVICE_MAX_DAYS:
            reason = f"Han pasado {elapsed} días desde el último servicio."
            severity = "ALTA"
        elif remaining <= SERVICE_WARNING_KM:
            reason = f"Faltan {remaining:.0f} km para el próximo servicio."
            severity = "MEDIA"
        else:
            continue

        alerts.append(
            {
                "vehicle": vehicle,
                "reason": reason,
                "severity": severity,
                "km_to_next_service": remaining,
                "days_since_service": elapsed,
            }
        )

    return sorted(
        alerts,
        key=lambda alert: (alert["severity"] != "ALTA", alert["km_to_next_service"]),
    )
