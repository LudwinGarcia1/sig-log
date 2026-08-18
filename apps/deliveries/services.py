"""Business rules for closing a delivery."""

from django.db import transaction

from apps.deliveries.models import DelayCause, Delivery


class DeliveryError(Exception):
    """Raised when a delivery operation violates a business rule."""


@transaction.atomic
def register_arrival(delivery, arrived_at, cause_code=None):
    """Close a delivery: compute the delay, demand a cause, free the vehicle.

    A late arrival without a stated cause is refused, because "¿cuáles son las
    causas principales de retraso?" cannot be answered from data nobody
    captured.
    """
    if delivery.status in Delivery.CLOSED_STATUSES:
        raise DeliveryError(
            f"La entrega {delivery.folio} ya está cerrada ({delivery.get_status_display()})."
        )

    reference_departure = delivery.actual_departure or delivery.scheduled_departure
    if arrived_at < reference_departure:
        raise DeliveryError("La llegada no puede ser anterior a la salida.")

    delivery.actual_arrival = arrived_at
    if delivery.actual_departure is None:
        delivery.actual_departure = delivery.scheduled_departure

    if delivery.is_delayed:
        if not cause_code:
            raise DeliveryError(
                "Una entrega con retraso requiere que se indique la causa."
            )
        try:
            delivery.delay_cause = DelayCause.objects.get(
                code=cause_code, is_active=True
            )
        except DelayCause.DoesNotExist as error:
            raise DeliveryError(f"Causa de retraso desconocida: {cause_code}.") from error
        delivery.status = "DELAYED"
    else:
        delivery.delay_cause = None
        delivery.status = "DELIVERED"

    delivery.save(
        update_fields=[
            "actual_arrival",
            "actual_departure",
            "delay_cause",
            "status",
            "updated_at",
        ]
    )

    vehicle = delivery.vehicle
    if vehicle.status == "ON_ROUTE":
        vehicle.status = "AVAILABLE"
        vehicle.save(update_fields=["status", "updated_at"])

    return delivery
