from apps.core.navigation import register
from apps.operators.views import OperatorCrud

urlpatterns = OperatorCrud.urlpatterns()
register("operator_list", "Operadores")
