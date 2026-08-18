from apps.core.views import CrudConfig
from apps.customers.forms import CustomerForm
from apps.customers.models import Customer


class CustomerCrud(CrudConfig):
    model = Customer
    form_class = CustomerForm
    list_columns = ["code", "business_name", "city", "state", "customer_type"]
    search_fields = ["code", "business_name", "tax_id", "city"]
    label = "Cliente"
    label_plural = "Clientes"
    slug = "customer"
    ordering = ("code",)
