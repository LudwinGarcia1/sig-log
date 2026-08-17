from django.contrib import admin
from django.urls import include, path

from apps.core.views import HomeView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", HomeView.as_view(), name="home"),
    path("clientes/", include("apps.customers.urls")),
    path("vehiculos/", include("apps.vehicles.urls")),
    path("operadores/", include("apps.operators.urls")),
    path("rutas/", include("apps.routes.urls")),
    path("entregas/", include("apps.deliveries.urls")),
    path("combustible/", include("apps.fuel.urls")),
    path("mantenimiento/", include("apps.maintenance.urls")),
    path("reportes/", include("apps.analytics.urls")),
]
