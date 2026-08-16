from apps.core.views import CrudConfig
from apps.operators.forms import OperatorForm
from apps.operators.models import Operator


class OperatorCrud(CrudConfig):
    model = Operator
    form_class = OperatorForm
    list_columns = [
        "employee_number", "first_name", "last_name", "license_type",
        "license_expiry", "status",
    ]
    search_fields = ["employee_number", "first_name", "last_name", "license_number"]
    label = "Operador"
    label_plural = "Operadores"
    slug = "operator"
    ordering = ("employee_number",)
