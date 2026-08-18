from apps.core.views import CrudConfig
from apps.routes.forms import RouteForm
from apps.routes.models import Route


class RouteCrud(CrudConfig):
    model = Route
    form_class = RouteForm
    list_columns = [
        "code", "name", "origin_city", "destination_city",
        "distance_km", "route_type", "zone",
    ]
    search_fields = ["code", "name", "origin_city", "destination_city", "zone"]
    label = "Ruta"
    label_plural = "Rutas"
    slug = "route"
    ordering = ("code",)
