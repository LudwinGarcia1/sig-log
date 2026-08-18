from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from apps.core.views import CrudConfig
from apps.maintenance.forms import MaintenanceForm
from apps.maintenance.models import Maintenance
from apps.maintenance.services import MaintenanceError, complete_maintenance


class MaintenanceCrud(CrudConfig):
    model = Maintenance
    form_class = MaintenanceForm
    list_columns = [
        "folio", "vehicle", "maintenance_type", "service_date",
        "odometer_km", "workshop", "total_cost", "status",
    ]
    search_fields = ["folio", "vehicle__plate", "vehicle__economic_number", "workshop"]
    label = "Mantenimiento"
    label_plural = "Mantenimientos"
    slug = "maintenance"
    ordering = ("-service_date",)
    extra_actions = [
        {
            "url_name": "maintenance_complete",
            "label": "Completar",
            "css": "btn btn-sm btn-outline-success",
            "method": "post",
            "show_if": "is_open",
        },
    ]


def maintenance_complete(request, pk):
    """HTTP wrapper around complete_maintenance."""
    if request.method != "POST":
        messages.error(request, "Operación no permitida.")
        return redirect("maintenance_list")
    order = get_object_or_404(Maintenance, pk=pk, is_active=True)
    try:
        complete_maintenance(order)
    except MaintenanceError as error:
        messages.error(request, str(error))
    else:
        messages.success(
            request,
            f"Mantenimiento {order.folio} completado. "
            f"Próximo servicio a los {order.next_service_km:.0f} km.",
        )
    return redirect("maintenance_list")
