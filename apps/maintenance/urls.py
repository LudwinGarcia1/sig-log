from django.urls import path

from apps.core.navigation import register
from apps.maintenance.views import MaintenanceCrud, maintenance_complete

urlpatterns = MaintenanceCrud.urlpatterns() + [
    path("<int:pk>/completar/", maintenance_complete, name="maintenance_complete"),
]
register("maintenance_list", "Mantenimiento")
