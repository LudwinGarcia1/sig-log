from django import forms

from apps.maintenance.models import Maintenance


class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = [
            "folio", "vehicle", "maintenance_type", "service_date", "odometer_km",
            "description", "workshop", "labor_cost", "parts_cost",
            "next_service_km", "days_out_of_service", "status",
        ]
        widgets = {
            "folio": forms.TextInput(attrs={"class": "form-control"}),
            "vehicle": forms.Select(attrs={"class": "form-select"}),
            "maintenance_type": forms.Select(attrs={"class": "form-select"}),
            "service_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "odometer_km": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "workshop": forms.TextInput(attrs={"class": "form-control"}),
            "labor_cost": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "parts_cost": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "next_service_km": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "days_out_of_service": forms.NumberInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def clean(self):
        cleaned = super().clean()
        labor = cleaned.get("labor_cost") or 0
        parts = cleaned.get("parts_cost") or 0
        if labor < 0 or parts < 0:
            raise forms.ValidationError("Los costos no pueden ser negativos.")
        return cleaned
