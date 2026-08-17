from django.urls import path

from apps.analytics import views
from apps.core.navigation import register

urlpatterns = [
    path("", views.dashboard, name="analytics_dashboard"),
    path("operacion/", views.operations, name="analytics_operations"),
    path("costos/", views.costs, name="analytics_costs"),
    path("mantenimiento/", views.alerts, name="analytics_alerts"),
    path("prediccion/", views.predictions, name="analytics_predictions"),
    path("conglomerados/", views.clusters, name="analytics_clusters"),
    path(
        "exportar/<slug:slug>.<str:fmt>",
        views.export_report,
        name="analytics_export",
    ),
]

register("analytics_dashboard", "Reportes", emphasised=True)
