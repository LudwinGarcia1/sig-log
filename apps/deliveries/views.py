from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.views import CrudConfig
from apps.deliveries.forms import ArrivalForm, DeliveryForm
from apps.deliveries.models import Delivery
from apps.deliveries.services import DeliveryError, register_arrival


class DeliveryCrud(CrudConfig):
    model = Delivery
    form_class = DeliveryForm
    list_columns = [
        "folio", "customer", "route", "vehicle", "operator",
        "scheduled_departure", "status",
    ]
    search_fields = ["folio", "customer__business_name", "route__code", "vehicle__plate"]
    label = "Entrega"
    label_plural = "Entregas"
    slug = "delivery"
    ordering = ("-scheduled_departure",)
    paginate_by = 25
    extra_actions = [
        {
            "url_name": "delivery_arrival",
            "label": "Registrar llegada",
            "css": "btn btn-sm btn-outline-success",
            "method": "get",
            "show_if": "is_open",
        },
    ]


def delivery_arrival(request, pk):
    """HTTP wrapper around register_arrival. Holds no business rule itself."""
    delivery = get_object_or_404(Delivery, pk=pk, is_active=True)
    form = ArrivalForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            register_arrival(
                delivery,
                form.cleaned_data["arrived_at"],
                form.cleaned_data["cause_code"] or None,
            )
        except DeliveryError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"Entrega {delivery.folio} cerrada.")
            return redirect("delivery_list")
    return render(
        request,
        "deliveries/arrival.html",
        {"delivery": delivery, "form": form, "crud_slug": "delivery"},
    )
