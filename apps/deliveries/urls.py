from django.urls import path

from apps.core.navigation import register
from apps.deliveries.views import DeliveryCrud, delivery_arrival

urlpatterns = DeliveryCrud.urlpatterns() + [
    path("<int:pk>/llegada/", delivery_arrival, name="delivery_arrival"),
]
register("delivery_list", "Entregas")
