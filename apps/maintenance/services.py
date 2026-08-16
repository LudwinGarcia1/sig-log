"""Closing a workshop order and refreshing the vehicle's service state."""

from django.db import transaction

from apps.maintenance.models import SERVICE_INTERVAL_KM, Maintenance


class MaintenanceError(Exception):
    """Raised when a maintenance operation violates a business rule."""


@transaction.atomic
def complete_maintenance(maintenance, next_service_km=None):
    """Close the order and push the new service window onto the vehicle.

    The vehicle owns its own service state, so ``maintenance_alerts()`` never
    has to reach into this app.
    """
    if maintenance.status == "COMPLETED":
        raise MaintenanceError(
            f"El mantenimiento {maintenance.folio} ya está completado."
        )

    vehicle = maintenance.vehicle
    if maintenance.odometer_km < vehicle.current_odometer_km:
        raise MaintenanceError(
            "El odómetro del servicio no puede ser menor al odómetro actual "
            f"del vehículo ({vehicle.current_odometer_km} km)."
        )

    target = (
        next_service_km
        if next_service_km is not None
        else maintenance.odometer_km + SERVICE_INTERVAL_KM
    )

    maintenance.next_service_km = target
    maintenance.status = "COMPLETED"
    maintenance.save(
        update_fields=["next_service_km", "status", "total_cost", "updated_at"]
    )

    vehicle.current_odometer_km = maintenance.odometer_km
    vehicle.next_service_km = target
    vehicle.last_service_date = maintenance.service_date
    vehicle.status = "AVAILABLE"
    vehicle.save(
        update_fields=[
            "current_odometer_km",
            "next_service_km",
            "last_service_date",
            "status",
            "updated_at",
        ]
    )

    return maintenance
