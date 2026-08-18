from apps.core.views import CrudConfig
from apps.vehicles.forms import VehicleForm
from apps.vehicles.models import Vehicle


class VehicleCrud(CrudConfig):
    model = Vehicle
    form_class = VehicleForm
    list_columns = [
        "economic_number", "plate", "brand", "model", "year",
        "vehicle_type", "current_odometer_km", "status",
    ]
    search_fields = ["economic_number", "plate", "brand", "model"]
    label = "Vehículo"
    label_plural = "Vehículos"
    slug = "vehicle"
    ordering = ("economic_number",)
