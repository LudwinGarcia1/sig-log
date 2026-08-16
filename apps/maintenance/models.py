from decimal import Decimal

from django.db import models

from apps.core.models import BaseModel
from apps.vehicles.models import Vehicle

SERVICE_INTERVAL_KM = Decimal("10000.00")


class Maintenance(BaseModel):
    """A workshop order against a vehicle."""

    TYPE_CHOICES = [
        ("PREVENTIVE", "Preventivo"),
        ("CORRECTIVE", "Correctivo"),
    ]
    STATUS_CHOICES = [
        ("SCHEDULED", "Programado"),
        ("IN_PROGRESS", "En proceso"),
        ("COMPLETED", "Completado"),
    ]

    folio = models.CharField("Folio", max_length=14, unique=True)
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.PROTECT, verbose_name="Vehículo"
    )
    maintenance_type = models.CharField(
        "Tipo", max_length=12, choices=TYPE_CHOICES, default="PREVENTIVE"
    )
    service_date = models.DateField("Fecha de servicio")
    odometer_km = models.DecimalField("Odómetro (km)", max_digits=12, decimal_places=2)
    description = models.TextField("Descripción")
    workshop = models.CharField("Taller", max_length=120)
    labor_cost = models.DecimalField(
        "Mano de obra", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    parts_cost = models.DecimalField(
        "Refacciones", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    total_cost = models.DecimalField(
        "Costo total", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    next_service_km = models.DecimalField(
        "Próximo servicio (km)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    days_out_of_service = models.PositiveSmallIntegerField(
        "Días fuera de servicio", default=0
    )
    status = models.CharField(
        "Estatus", max_length=12, choices=STATUS_CHOICES, default="SCHEDULED"
    )

    class Meta:
        verbose_name = "Mantenimiento"
        verbose_name_plural = "Mantenimientos"
        ordering = ["-service_date"]
        indexes = [models.Index(fields=["vehicle", "service_date"])]

    def __str__(self):
        return self.folio

    def save(self, *args, **kwargs):
        self.total_cost = self.labor_cost + self.parts_cost
        super().save(*args, **kwargs)
