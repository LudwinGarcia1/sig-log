from django import forms

from apps.routes.models import Route


class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = [
            "code", "name", "origin_city", "destination_city", "distance_km",
            "estimated_duration_min", "route_type", "zone", "toll_cost",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "origin_city": forms.TextInput(attrs={"class": "form-control"}),
            "destination_city": forms.TextInput(attrs={"class": "form-control"}),
            "distance_km": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "estimated_duration_min": forms.NumberInput(attrs={"class": "form-control"}),
            "route_type": forms.Select(attrs={"class": "form-select"}),
            "zone": forms.TextInput(attrs={"class": "form-control"}),
            "toll_cost": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def clean_distance_km(self):
        distance = self.cleaned_data["distance_km"]
        if distance <= 0:
            raise forms.ValidationError("La distancia debe ser mayor que cero.")
        return distance
