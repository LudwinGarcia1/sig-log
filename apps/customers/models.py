from django.db import models

from apps.core.models import BaseModel


class Customer(BaseModel):
    """A company that receives shipments."""

    TYPE_CHOICES = [
        ("PREMIUM", "Premium"),
        ("REGULAR", "Regular"),
        ("OCCASIONAL", "Ocasional"),
    ]

    code = models.CharField("Código", max_length=10, unique=True)
    business_name = models.CharField("Razón social", max_length=150)
    tax_id = models.CharField("RFC", max_length=13)
    contact_name = models.CharField("Contacto", max_length=120)
    phone = models.CharField("Teléfono", max_length=20)
    email = models.EmailField("Correo", blank=True)
    address = models.CharField("Dirección", max_length=200)
    city = models.CharField("Ciudad", max_length=80)
    state = models.CharField("Estado", max_length=80)
    postal_code = models.CharField("Código postal", max_length=5)
    customer_type = models.CharField(
        "Tipo de cliente", max_length=12, choices=TYPE_CHOICES, default="REGULAR"
    )

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.business_name}"

    @property
    def total_deliveries(self):
        return self.delivery_set.count()
