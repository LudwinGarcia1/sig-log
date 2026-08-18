from apps.core.navigation import register
from apps.routes.views import RouteCrud

urlpatterns = RouteCrud.urlpatterns()
register("route_list", "Rutas")
