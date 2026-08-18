from django.db import models

from apps.core.models import BaseModel


class Widget(BaseModel):
    """Test-only entity that exercises the generic CRUD engine."""

    code = models.CharField("Código", max_length=10, unique=True)
    name = models.CharField("Nombre", max_length=60)
    size = models.CharField(
        "Tamaño",
        max_length=6,
        choices=[("SMALL", "Chico"), ("LARGE", "Grande")],
        default="SMALL",
    )

    class Meta:
        app_label = "core"

    def __str__(self):
        return self.code
