from django.db import models


class BaseModel(models.Model):
    """Audit fields shared by every business entity."""

    created_at = models.DateTimeField("Creado", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado", auto_now=True, db_index=True)
    is_active = models.BooleanField("Activo", default=True)

    class Meta:
        abstract = True

    def deactivate(self):
        """Soft delete: the row stays for auditing and for the ETL."""
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])
