from apps.core.navigation import register
from apps.fuel.views import FuelLoadCrud

urlpatterns = FuelLoadCrud.urlpatterns()
register("fuelload_list", "Combustible")
