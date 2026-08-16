from apps.core.views import CrudConfig
from apps.fuel.forms import FuelLoadForm
from apps.fuel.models import FuelLoad


class FuelLoadCrud(CrudConfig):
    model = FuelLoad
    form_class = FuelLoadForm
    list_columns = [
        "folio", "vehicle", "load_datetime", "station_name",
        "liters", "price_per_liter", "total_cost", "odometer_km",
    ]
    search_fields = ["folio", "vehicle__plate", "vehicle__economic_number", "station_name"]
    label = "Carga de combustible"
    label_plural = "Cargas de combustible"
    slug = "fuelload"
    ordering = ("-load_datetime",)
    paginate_by = 25
