from django.contrib import admin
from django.urls import include, path

from apps.core.views import HomeView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", HomeView.as_view(), name="home"),
    path("clientes/", include("apps.customers.urls")),
    path("operadores/", include("apps.operators.urls")),
    path("rutas/", include("apps.routes.urls")),
]
