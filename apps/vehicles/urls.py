from apps.core.navigation import register
from apps.vehicles.views import VehicleCrud

urlpatterns = VehicleCrud.urlpatterns()
register("vehicle_list", "Vehículos")
