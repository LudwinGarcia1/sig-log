from django import forms

from apps.fuel.models import FuelLoad


class FuelLoadForm(forms.ModelForm):
    class Meta:
        model = FuelLoad
        fields = [
            "folio", "vehicle", "operator", "delivery", "load_datetime",
            "station_name", "liters", "price_per_liter", "odometer_km",
        ]
        widgets = {
            "folio": forms.TextInput(attrs={"class": "form-control"}),
            "vehicle": forms.Select(attrs={"class": "form-select"}),
            "operator": forms.Select(attrs={"class": "form-select"}),
            "delivery": forms.Select(attrs={"class": "form-select"}),
            "load_datetime": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "station_name": forms.TextInput(attrs={"class": "form-control"}),
            "liters": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "price_per_liter": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "odometer_km": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["load_datetime"].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean_liters(self):
        liters = self.cleaned_data["liters"]
        if liters <= 0:
            raise forms.ValidationError("Los litros deben ser mayores que cero.")
        return liters

    def clean(self):
        cleaned = super().clean()
        vehicle = cleaned.get("vehicle")
        liters = cleaned.get("liters")
        odometer = cleaned.get("odometer_km")
        if vehicle and liters and liters > vehicle.tank_capacity_l * 2:
            raise forms.ValidationError(
                "Los litros superan el doble de la capacidad del tanque; verifica la captura."
            )
        if vehicle and odometer is not None and odometer < 0:
            raise forms.ValidationError("El odómetro no puede ser negativo.")
        return cleaned
