from decimal import Decimal

from django.db import models

from apps.core.models import BaseModel


class Route(BaseModel):
    """A fixed origin-destination corridor the fleet serves."""

    TYPE_CHOICES = [
        ("LOCAL", "Local"),
        ("REGIONAL", "Regional"),
        ("FORANEA", "Foránea"),
    ]

    code = models.CharField("Código", max_length=10, unique=True)
    name = models.CharField("Nombre", max_length=150)
    origin_city = models.CharField("Ciudad origen", max_length=80)
    destination_city = models.CharField("Ciudad destino", max_length=80)
    distance_km = models.DecimalField("Distancia (km)", max_digits=8, decimal_places=2)
    estimated_duration_min = models.PositiveIntegerField("Duración estimada (min)")
    route_type = models.CharField(
        "Tipo de ruta", max_length=10, choices=TYPE_CHOICES, default="REGIONAL"
    )
    zone = models.CharField("Zona", max_length=40)
    toll_cost = models.DecimalField(
        "Casetas", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )

    class Meta:
        verbose_name = "Ruta"
        verbose_name_plural = "Rutas"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"

    @property
    def estimated_average_speed(self):
        """Average km/h implied by the planned duration."""
        if not self.estimated_duration_min:
            return Decimal("0.00")
        hours = Decimal(self.estimated_duration_min) / Decimal("60")
        return (self.distance_km / hours).quantize(Decimal("0.01"))
