"""Capture form for a prospective delivery.

The form asks only for facts that exist before departure — the same contract
the classifier was trained under. It derives the remaining feature columns from
the chosen route so the user cannot introduce an inconsistency.
"""

from datetime import timedelta

from django import forms

from apps.analytics import queries
from apps.routes.models import Route
from warehouse.etl.cleaning import distance_range
from warehouse.models import TIME_BANDS

DAY_CHOICES = [
    (0, "Lunes"), (1, "Martes"), (2, "Miércoles"), (3, "Jueves"),
    (4, "Viernes"), (5, "Sábado"), (6, "Domingo"),
]
VEHICLE_TYPE_CHOICES = [
    ("TRUCK", "Camión"), ("VAN", "Camioneta"),
    ("TRAILER", "Tráiler"), ("PICKUP", "Pick-up"),
]
AGE_CHOICES = [("0-3", "0 a 3 años"), ("4-8", "4 a 8 años"), ("9+", "9 años o más")]
SENIORITY_CHOICES = [
    ("0-2", "0 a 2 años"), ("3-5", "3 a 5 años"), ("6+", "6 años o más"),
]
CUSTOMER_TYPE_CHOICES = [
    ("PREMIUM", "Premium"), ("REGULAR", "Regular"), ("OCCASIONAL", "Ocasional"),
]


class DelayPredictionForm(forms.Form):
    route = forms.ModelChoiceField(
        label="Ruta", queryset=Route.objects.filter(is_active=True).order_by("code"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    departure_hour = forms.IntegerField(
        label="Hora de salida", min_value=0, max_value=23, initial=8,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    day_of_week = forms.TypedChoiceField(
        label="Día de la semana", choices=DAY_CHOICES, coerce=int, initial=1,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    cargo_weight_kg = forms.DecimalField(
        label="Peso de carga (kg)", min_value=1, initial=5000,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    packages_count = forms.IntegerField(
        label="Bultos", min_value=1, initial=40,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    vehicle_type = forms.ChoiceField(
        label="Tipo de vehículo", choices=VEHICLE_TYPE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    vehicle_age_range = forms.ChoiceField(
        label="Antigüedad del vehículo", choices=AGE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    operator_seniority_range = forms.ChoiceField(
        label="Antigüedad del operador", choices=SENIORITY_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    customer_type = forms.ChoiceField(
        label="Tipo de cliente", choices=CUSTOMER_TYPE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def to_features(self):
        """Build the exact feature mapping the pipeline expects."""
        data = self.cleaned_data
        route = data["route"]
        hour = data["departure_hour"]
        day = data["day_of_week"]
        return {
            "distance_km": float(route.distance_km),
            "planned_duration_min": int(route.estimated_duration_min),
            "cargo_weight_kg": float(data["cargo_weight_kg"]),
            "packages_count": int(data["packages_count"]),
            "day_of_week": day,
            "route_code": route.code,
            "route_type": route.route_type,
            "zone": route.zone,
            "distance_range": distance_range(route.distance_km),
            "time_band": TIME_BANDS[hour],
            "vehicle_type": data["vehicle_type"],
            "vehicle_age_range": data["vehicle_age_range"],
            "operator_seniority_range": data["operator_seniority_range"],
            "customer_type": data["customer_type"],
            "is_weekend": "True" if day >= 5 else "False",
        }


class PeriodForm(forms.Form):
    """Rango de fechas con el que se acotan las pantallas de análisis.

    Los atajos se resuelven contra la última fecha con datos, que la vista
    entrega en ``last_day``; contarlos desde hoy dejaría la pantalla vacía en
    cuanto el almacén se quede atrás.
    """

    PRESET_DAYS = {"mes": 30, "trimestre": 91, "anio": 365}
    PRESETS = [
        ("todo", "Todo"),
        ("mes", "Último mes"),
        ("trimestre", "Último trimestre"),
        ("anio", "Último año"),
    ]

    start = forms.DateField(
        required=False, label="Desde",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    end = forms.DateField(
        required=False, label="Hasta",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    preset = forms.ChoiceField(
        required=False, choices=PRESETS, widget=forms.HiddenInput
    )

    def __init__(self, *args, last_day=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_day = last_day

    def clean(self):
        data = super().clean()
        start, end = data.get("start"), data.get("end")
        if start and end and start > end:
            raise forms.ValidationError(
                "La fecha inicial no puede ser posterior a la final."
            )
        return data

    def period(self):
        """El periodo elegido; todo el histórico si no se pidió nada válido."""
        if not self.is_bound or not self.is_valid():
            return queries.Period()
        preset = self.cleaned_data.get("preset")
        if preset in self.PRESET_DAYS and self.last_day:
            days = self.PRESET_DAYS[preset]
            return queries.Period(
                start=self.last_day - timedelta(days=days), end=self.last_day
            )
        if preset == "todo":
            return queries.Period()
        return queries.Period(
            start=self.cleaned_data.get("start"), end=self.cleaned_data.get("end")
        )
