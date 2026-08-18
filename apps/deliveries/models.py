from decimal import Decimal

from django.db import models

from apps.core.models import BaseModel
from apps.customers.models import Customer
from apps.operators.models import Operator
from apps.routes.models import Route
from apps.vehicles.models import Vehicle

DELAY_TOLERANCE_MINUTES = 15


class DelayCause(BaseModel):
    """Catalogue that turns "why was it late?" into a query."""

    CATEGORY_CHOICES = [
        ("EXTERNA", "Externa"),
        ("INTERNA", "Interna"),
        ("MECANICA", "Mecánica"),
    ]

    code = models.CharField("Código", max_length=20, unique=True)
    name = models.CharField("Causa", max_length=80)
    category = models.CharField(
        "Categoría", max_length=10, choices=CATEGORY_CHOICES, default="EXTERNA"
    )

    class Meta:
        verbose_name = "Causa de retraso"
        verbose_name_plural = "Causas de retraso"
        ordering = ["code"]

    def __str__(self):
        return self.name


class Delivery(BaseModel):
    """A single shipment from origin to a customer destination."""

    STATUS_CHOICES = [
        ("SCHEDULED", "Programada"),
        ("IN_TRANSIT", "En tránsito"),
        ("DELIVERED", "Entregada"),
        ("DELAYED", "Entregada con retraso"),
        ("CANCELLED", "Cancelada"),
    ]
    CLOSED_STATUSES = ("DELIVERED", "DELAYED", "CANCELLED")

    folio = models.CharField("Folio", max_length=14, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, verbose_name="Cliente"
    )
    route = models.ForeignKey(Route, on_delete=models.PROTECT, verbose_name="Ruta")
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.PROTECT, verbose_name="Vehículo"
    )
    operator = models.ForeignKey(
        Operator, on_delete=models.PROTECT, verbose_name="Operador"
    )
    delay_cause = models.ForeignKey(
        DelayCause,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Causa de retraso",
    )
    scheduled_departure = models.DateTimeField("Salida programada")
    actual_departure = models.DateTimeField("Salida real", null=True, blank=True)
    scheduled_arrival = models.DateTimeField("Llegada programada")
    actual_arrival = models.DateTimeField("Llegada real", null=True, blank=True)
    cargo_weight_kg = models.DecimalField(
        "Peso de carga (kg)", max_digits=10, decimal_places=2
    )
    packages_count = models.PositiveIntegerField("Bultos", default=1)
    declared_value = models.DecimalField(
        "Valor declarado", max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    freight_cost = models.DecimalField("Flete", max_digits=10, decimal_places=2)
    status = models.CharField(
        "Estatus", max_length=12, choices=STATUS_CHOICES, default="SCHEDULED"
    )

    class Meta:
        verbose_name = "Entrega"
        verbose_name_plural = "Entregas"
        ordering = ["-scheduled_departure"]
        indexes = [
            models.Index(fields=["scheduled_departure"]),
            models.Index(fields=["route", "scheduled_departure"]),
            models.Index(fields=["vehicle", "scheduled_departure"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.folio

    @property
    def delay_minutes(self):
        """Minutes past the scheduled arrival; zero when early or open."""
        if self.actual_arrival is None:
            return 0
        difference = (self.actual_arrival - self.scheduled_arrival).total_seconds() / 60
        return max(int(round(difference)), 0)

    @property
    def is_delayed(self):
        return self.delay_minutes > DELAY_TOLERANCE_MINUTES

    @property
    def is_open(self):
        return self.status not in Delivery.CLOSED_STATUSES

    @property
    def transit_minutes(self):
        if self.actual_arrival is None or self.actual_departure is None:
            return None
        return int(
            round((self.actual_arrival - self.actual_departure).total_seconds() / 60)
        )
