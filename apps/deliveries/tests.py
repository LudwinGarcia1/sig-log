from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from apps.core.tests.base import AuthenticatedTestCase
from apps.customers.models import Customer
from apps.deliveries.models import DelayCause, Delivery
from apps.deliveries.services import DeliveryError, register_arrival
from apps.operators.models import Operator
from apps.routes.models import Route
from apps.vehicles.models import Vehicle


class DeliveryTestCase(AuthenticatedTestCase):
    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create(
            code="CLI-0001", business_name="Distribuidora del Valle",
            tax_id="DVA010203AB1", contact_name="Luis Mora", phone="7221234567",
            address="Av. Reforma 100", city="Toluca", state="México",
            postal_code="50000", customer_type="PREMIUM",
        )
        self.route = Route.objects.create(
            code="RUT-001", name="Toluca — CDMX", origin_city="Toluca",
            destination_city="Ciudad de México", distance_km=Decimal("120.00"),
            estimated_duration_min=120, route_type="REGIONAL", zone="CENTRO",
            toll_cost=Decimal("180.00"),
        )
        self.vehicle = Vehicle.objects.create(
            plate="ABC1234", economic_number="EC-0001", brand="Freightliner",
            model="Cascadia", year=date.today().year - 3, vehicle_type="TRUCK",
            cargo_capacity_kg=Decimal("12000.00"), fuel_type="DIESEL",
            tank_capacity_l=Decimal("300.00"), current_odometer_km=Decimal("100000.00"),
            acquisition_date=date.today() - timedelta(days=1000),
            next_service_km=Decimal("110000.00"),
            last_service_date=date.today() - timedelta(days=20),
            status="ON_ROUTE",
        )
        self.operator = Operator.objects.create(
            employee_number="OP-0001", first_name="Ana", last_name="Ruiz",
            license_number="LF-99887", license_type="C",
            license_expiry=date.today() + timedelta(days=365),
            hire_date=date.today() - timedelta(days=1200), phone="5512345678",
        )
        self.traffic = DelayCause.objects.create(
            code="TRAFICO", name="Tráfico", category="EXTERNA"
        )
        DelayCause.objects.create(
            code="NO_ESPECIFICADA", name="No especificada", category="EXTERNA"
        )
        self.departure = timezone.now() - timedelta(hours=4)

    def _delivery(self, **overrides):
        defaults = {
            "folio": "ENT-2026-00001",
            "customer": self.customer,
            "route": self.route,
            "vehicle": self.vehicle,
            "operator": self.operator,
            "scheduled_departure": self.departure,
            "actual_departure": self.departure,
            "scheduled_arrival": self.departure + timedelta(minutes=120),
            "cargo_weight_kg": Decimal("5000.00"),
            "packages_count": 40,
            "declared_value": Decimal("250000.00"),
            "freight_cost": Decimal("4800.00"),
            "status": "IN_TRANSIT",
        }
        defaults.update(overrides)
        return Delivery.objects.create(**defaults)


class DeliveryBehaviourTest(DeliveryTestCase):
    def test_delay_minutes_is_zero_before_arrival(self):
        self.assertEqual(self._delivery().delay_minutes, 0)

    def test_delay_minutes_counts_late_arrival(self):
        delivery = self._delivery(
            actual_arrival=self.departure + timedelta(minutes=155)
        )
        self.assertEqual(delivery.delay_minutes, 35)

    def test_delay_minutes_is_zero_when_early(self):
        delivery = self._delivery(
            actual_arrival=self.departure + timedelta(minutes=100)
        )
        self.assertEqual(delivery.delay_minutes, 0)

    def test_is_delayed_uses_tolerance_of_fifteen_minutes(self):
        on_time = self._delivery(
            actual_arrival=self.departure + timedelta(minutes=130)
        )
        self.assertFalse(on_time.is_delayed)
        late = self._delivery(
            folio="ENT-2026-00002",
            actual_arrival=self.departure + timedelta(minutes=141),
        )
        self.assertTrue(late.is_delayed)

    def test_is_delayed_at_exactly_the_fifteen_minute_boundary(self):
        exactly_on_tolerance = self._delivery(
            folio="ENT-2026-00003",
            actual_arrival=self.departure + timedelta(minutes=120 + 15),
        )
        self.assertFalse(exactly_on_tolerance.is_delayed)
        one_minute_over = self._delivery(
            folio="ENT-2026-00004",
            actual_arrival=self.departure + timedelta(minutes=120 + 16),
        )
        self.assertTrue(one_minute_over.is_delayed)

    def test_transit_minutes_is_none_without_arrival(self):
        self.assertIsNone(self._delivery().transit_minutes)

    def test_transit_minutes_measures_departure_to_arrival(self):
        delivery = self._delivery(
            actual_arrival=self.departure + timedelta(minutes=155)
        )
        self.assertEqual(delivery.transit_minutes, 155)


class RegisterArrivalTest(DeliveryTestCase):
    def test_on_time_arrival_marks_delivered_and_frees_vehicle(self):
        delivery = self._delivery()
        result = register_arrival(
            delivery, self.departure + timedelta(minutes=118)
        )
        self.assertEqual(result.status, "DELIVERED")
        self.assertIsNone(result.delay_cause)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, "AVAILABLE")

    def test_late_arrival_requires_a_cause(self):
        delivery = self._delivery()
        with self.assertRaises(DeliveryError):
            register_arrival(delivery, self.departure + timedelta(minutes=200))

    def test_late_arrival_with_cause_marks_delayed(self):
        delivery = self._delivery()
        result = register_arrival(
            delivery, self.departure + timedelta(minutes=200), cause_code="TRAFICO"
        )
        self.assertEqual(result.status, "DELAYED")
        self.assertEqual(result.delay_cause, self.traffic)
        self.assertEqual(result.delay_minutes, 80)

    def test_arrival_before_departure_is_rejected(self):
        delivery = self._delivery()
        with self.assertRaises(DeliveryError):
            register_arrival(delivery, self.departure - timedelta(minutes=5))

    def test_already_closed_delivery_is_rejected(self):
        delivery = self._delivery(status="DELIVERED")
        with self.assertRaises(DeliveryError):
            register_arrival(delivery, self.departure + timedelta(minutes=118))

    def test_unknown_cause_code_is_rejected(self):
        delivery = self._delivery()
        with self.assertRaises(DeliveryError):
            register_arrival(
                delivery,
                self.departure + timedelta(minutes=200),
                cause_code="INEXISTENTE",
            )


class DeliveryListArrivalButtonTest(DeliveryTestCase):
    def test_open_delivery_shows_the_arrival_link(self):
        delivery = self._delivery(status="IN_TRANSIT")
        response = self.client.get(reverse("delivery_list"))
        self.assertContains(response, reverse("delivery_arrival", args=[delivery.pk]))

    def test_closed_delivery_does_not_show_the_arrival_link(self):
        delivery = self._delivery(status="DELIVERED", actual_arrival=self.departure + timedelta(minutes=118))
        response = self.client.get(reverse("delivery_list"))
        self.assertNotContains(response, reverse("delivery_arrival", args=[delivery.pk]))
