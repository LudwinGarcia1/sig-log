from datetime import date

from django import forms

from apps.vehicles.models import Vehicle


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "plate", "economic_number", "brand", "model", "year", "vehicle_type",
            "cargo_capacity_kg", "fuel_type", "tank_capacity_l",
            "current_odometer_km", "acquisition_date", "next_service_km",
            "last_service_date", "status",
        ]
        widgets = {
            "plate": forms.TextInput(attrs={"class": "form-control"}),
            "economic_number": forms.TextInput(attrs={"class": "form-control"}),
            "brand": forms.TextInput(attrs={"class": "form-control"}),
            "model": forms.TextInput(attrs={"class": "form-control"}),
            "year": forms.NumberInput(attrs={"class": "form-control"}),
            "vehicle_type": forms.Select(attrs={"class": "form-select"}),
            "cargo_capacity_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "fuel_type": forms.Select(attrs={"class": "form-select"}),
            "tank_capacity_l": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "current_odometer_km": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "acquisition_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "next_service_km": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "last_service_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_plate(self):
        return self.cleaned_data["plate"].strip().upper().replace("-", "")

    def clean_year(self):
        year = self.cleaned_data["year"]
        if year < 1980 or year > date.today().year + 1:
            raise forms.ValidationError("Año fuera de un rango razonable.")
        return year
