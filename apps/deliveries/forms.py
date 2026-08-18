from django import forms

from apps.deliveries.models import DelayCause, Delivery


class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = [
            "folio", "customer", "route", "vehicle", "operator",
            "scheduled_departure", "actual_departure",
            "scheduled_arrival", "actual_arrival",
            "cargo_weight_kg", "packages_count", "declared_value",
            "freight_cost", "delay_cause", "status",
        ]
        widgets = {
            "folio": forms.TextInput(attrs={"class": "form-control"}),
            "customer": forms.Select(attrs={"class": "form-select"}),
            "route": forms.Select(attrs={"class": "form-select"}),
            "vehicle": forms.Select(attrs={"class": "form-select"}),
            "operator": forms.Select(attrs={"class": "form-select"}),
            "scheduled_departure": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "actual_departure": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "scheduled_arrival": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "actual_arrival": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "cargo_weight_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "packages_count": forms.NumberInput(attrs={"class": "form-control"}),
            "declared_value": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "freight_cost": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "delay_cause": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in (
            "scheduled_departure", "actual_departure",
            "scheduled_arrival", "actual_arrival",
        ):
            self.fields[field_name].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean(self):
        cleaned = super().clean()
        departure = cleaned.get("scheduled_departure")
        arrival = cleaned.get("scheduled_arrival")
        if departure and arrival and arrival <= departure:
            raise forms.ValidationError(
                "La llegada programada debe ser posterior a la salida programada."
            )
        weight = cleaned.get("cargo_weight_kg")
        vehicle = cleaned.get("vehicle")
        if weight and vehicle and weight > vehicle.cargo_capacity_kg:
            raise forms.ValidationError(
                f"El peso excede la capacidad del vehículo "
                f"({vehicle.cargo_capacity_kg} kg)."
            )
        return cleaned


class ArrivalForm(forms.Form):
    """Captures the closing of a delivery."""

    arrived_at = forms.DateTimeField(
        label="Llegada real",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
    )
    cause_code = forms.ChoiceField(
        label="Causa de retraso (si aplica)",
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cause_code"].choices = [("", "— Sin retraso —")] + [
            (cause.code, cause.name)
            for cause in DelayCause.objects.filter(is_active=True).order_by("name")
        ]
