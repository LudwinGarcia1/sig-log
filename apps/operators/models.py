from datetime import date

from django.db import models

from apps.core.models import BaseModel


class Operator(BaseModel):
    """A driver assigned to deliveries."""

    LICENSE_CHOICES = [
        ("A", "A — Automovilista"),
        ("B", "B — Chofer"),
        ("C", "C — Carga federal"),
        ("E", "E — Doble remolque"),
    ]
    STATUS_CHOICES = [
        ("ACTIVE", "Activo"),
        ("VACATION", "Vacaciones"),
        ("INACTIVE", "Inactivo"),
    ]

    employee_number = models.CharField("Número de empleado", max_length=10, unique=True)
    first_name = models.CharField("Nombre", max_length=80)
    last_name = models.CharField("Apellidos", max_length=80)
    license_number = models.CharField("Número de licencia", max_length=20)
    license_type = models.CharField(
        "Tipo de licencia", max_length=2, choices=LICENSE_CHOICES, default="C"
    )
    license_expiry = models.DateField("Vigencia de licencia")
    hire_date = models.DateField("Fecha de ingreso")
    phone = models.CharField("Teléfono", max_length=20)
    status = models.CharField(
        "Estatus", max_length=12, choices=STATUS_CHOICES, default="ACTIVE"
    )

    class Meta:
        verbose_name = "Operador"
        verbose_name_plural = "Operadores"
        ordering = ["employee_number"]

    def __str__(self):
        return f"{self.employee_number} — {self.full_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def license_is_valid(self):
        return self.license_expiry >= date.today()

    @property
    def seniority_years(self):
        today = date.today()
        years = today.year - self.hire_date.year
        if (today.month, today.day) < (self.hire_date.month, self.hire_date.day):
            years -= 1
        return max(years, 0)
