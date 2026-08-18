from datetime import date
from decimal import Decimal

from django.db import models

from apps.core.models import BaseModel

SERVICE_WARNING_KM = Decimal("1000.00")
SERVICE_MAX_DAYS = 180


class Vehicle(BaseModel):
    """A unit in the fleet."""

    TYPE_CHOICES = [
        ("TRUCK", "Camión"),
        ("VAN", "Camioneta"),
        ("TRAILER", "Tráiler"),
        ("PICKUP", "Pick-up"),
    ]
    FUEL_CHOICES = [("DIESEL", "Diésel"), ("GASOLINE", "Gasolina")]
    STATUS_CHOICES = [
        ("AVAILABLE", "Disponible"),
        ("ON_ROUTE", "En ruta"),
        ("IN_MAINTENANCE", "En mantenimiento"),
        ("OUT_OF_SERVICE", "Fuera de servicio"),
    ]

    plate = models.CharField("Placa", max_length=10, unique=True)
    economic_number = models.CharField("Número económico", max_length=10, unique=True)
    brand = models.CharField("Marca", max_length=60)
    model = models.CharField("Modelo", max_length=60)
    year = models.PositiveSmallIntegerField("Año")
    vehicle_type = models.CharField(
        "Tipo", max_length=10, choices=TYPE_CHOICES, default="TRUCK"
    )
    cargo_capacity_kg = models.DecimalField(
        "Capacidad de carga (kg)", max_digits=10, decimal_places=2
    )
    fuel_type = models.CharField(
        "Combustible", max_length=10, choices=FUEL_CHOICES, default="DIESEL"
    )
    tank_capacity_l = models.DecimalField(
        "Capacidad de tanque (L)", max_digits=8, decimal_places=2
    )
    current_odometer_km = models.DecimalField(
        "Odómetro (km)", max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    acquisition_date = models.DateField("Fecha de adquisición")
    next_service_km = models.DecimalField(
        "Próximo servicio (km)", max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    last_service_date = models.DateField("Último servicio", null=True, blank=True)
    status = models.CharField(
        "Estatus", max_length=16, choices=STATUS_CHOICES, default="AVAILABLE"
    )

    class Meta:
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"
        ordering = ["economic_number"]

    def __str__(self):
        return f"{self.economic_number} — {self.plate}"

    @property
    def age_years(self):
        return max(date.today().year - self.year, 0)

    @property
    def age_range(self):
        """Bucket used as a categorical feature and as a DW attribute."""
        age = self.age_years
        if age <= 3:
            return "0-3"
        if age <= 8:
            return "4-8"
        return "9+"

    @property
    def km_to_next_service(self):
        return self.next_service_km - self.current_odometer_km

    @property
    def days_since_service(self):
        if self.last_service_date is None:
            return None
        return (date.today() - self.last_service_date).days

    @property
    def needs_maintenance(self):
        if self.km_to_next_service <= SERVICE_WARNING_KM:
            return True
        elapsed = self.days_since_service
        return elapsed is None or elapsed > SERVICE_MAX_DAYS
