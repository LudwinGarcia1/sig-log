from decimal import Decimal

from django.db import models

from apps.core.models import BaseModel
from apps.deliveries.models import Delivery
from apps.operators.models import Operator
from apps.vehicles.models import Vehicle


class FuelLoad(BaseModel):
    """A single refuelling event."""

    folio = models.CharField("Folio", max_length=14, unique=True)
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.PROTECT, verbose_name="Vehículo"
    )
    operator = models.ForeignKey(
        Operator, on_delete=models.PROTECT, verbose_name="Operador"
    )
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Entrega asociada",
    )
    load_datetime = models.DateTimeField("Fecha y hora de carga")
    station_name = models.CharField("Estación", max_length=120)
    liters = models.DecimalField("Litros", max_digits=8, decimal_places=2)
    price_per_liter = models.DecimalField(
        "Precio por litro", max_digits=6, decimal_places=2
    )
    total_cost = models.DecimalField(
        "Costo total", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    odometer_km = models.DecimalField("Odómetro (km)", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Carga de combustible"
        verbose_name_plural = "Cargas de combustible"
        ordering = ["-load_datetime"]
        indexes = [models.Index(fields=["vehicle", "load_datetime"])]

    def __str__(self):
        return self.folio

    def save(self, *args, **kwargs):
        self.total_cost = (self.liters * self.price_per_liter).quantize(
            Decimal("0.01")
        )
        super().save(*args, **kwargs)

    @property
    def previous_load(self):
        """The same vehicle's previous refuelling, if any."""
        return (
            FuelLoad.objects.filter(
                vehicle=self.vehicle,
                load_datetime__lt=self.load_datetime,
                is_active=True,
            )
            .order_by("-load_datetime")
            .first()
        )

    @property
    def km_traveled(self):
        previous = self.previous_load
        if previous is None:
            return None
        return self.odometer_km - previous.odometer_km

    @property
    def efficiency_km_per_liter(self):
        distance = self.km_traveled
        if distance is None or distance <= 0 or self.liters <= 0:
            return None
        return (distance / self.liters).quantize(Decimal("0.01"))
