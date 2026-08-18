from apps.core.navigation import register
from apps.customers.views import CustomerCrud

urlpatterns = CustomerCrud.urlpatterns()
register("customer_list", "Clientes")
