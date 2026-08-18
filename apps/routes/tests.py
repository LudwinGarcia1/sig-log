from decimal import Decimal

from django.test import TestCase

from apps.routes.models import Route


class RouteBehaviourTest(TestCase):
    def test_estimated_average_speed_is_km_over_hours(self):
        route = Route.objects.create(
            code="RUT-001",
            name="Toluca — CDMX",
            origin_city="Toluca",
            destination_city="Ciudad de México",
            distance_km=Decimal("120.00"),
            estimated_duration_min=120,
            route_type="REGIONAL",
            zone="CENTRO",
            toll_cost=Decimal("180.00"),
        )
        self.assertEqual(route.estimated_average_speed, Decimal("60.00"))

    def test_estimated_average_speed_is_zero_when_duration_missing(self):
        route = Route.objects.create(
            code="RUT-002",
            name="Ruta sin duración",
            origin_city="Toluca",
            destination_city="Lerma",
            distance_km=Decimal("15.00"),
            estimated_duration_min=0,
            route_type="LOCAL",
            zone="METROPOLITANA",
            toll_cost=Decimal("0.00"),
        )
        self.assertEqual(route.estimated_average_speed, Decimal("0.00"))
