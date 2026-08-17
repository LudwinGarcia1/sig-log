from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.maintenance.models import Maintenance
from apps.maintenance.services import MaintenanceError, complete_maintenance
from apps.vehicles.models import Vehicle


class MaintenanceTestCase(TestCase):
    def setUp(self):
        self.vehicle = Vehicle.objects.create(
            plate="ABC1234", economic_number="EC-0001", brand="Freightliner",
            model="Cascadia", year=date.today().year - 3, vehicle_type="TRUCK",
            cargo_capacity_kg=Decimal("12000.00"), fuel_type="DIESEL",
            tank_capacity_l=Decimal("300.00"), current_odometer_km=Decimal("109000.00"),
            acquisition_date=date.today() - timedelta(days=1000),
            next_service_km=Decimal("110000.00"),
            last_service_date=date.today() - timedelta(days=190),
            status="IN_MAINTENANCE",
        )

    def _order(self, **overrides):
        defaults = {
            "folio": "MTO-0001",
            "vehicle": self.vehicle,
            "maintenance_type": "PREVENTIVE",
            "service_date": date.today(),
            "odometer_km": Decimal("110200.00"),
            "description": "Cambio de aceite y filtros",
            "workshop": "Taller Central",
            "labor_cost": Decimal("1500.00"),
            "parts_cost": Decimal("3200.00"),
            "days_out_of_service": 1,
            "status": "IN_PROGRESS",
        }
        defaults.update(overrides)
        return Maintenance.objects.create(**defaults)


class MaintenanceBehaviourTest(MaintenanceTestCase):
    def test_total_cost_is_computed_on_save(self):
        self.assertEqual(self._order().total_cost, Decimal("4700.00"))


class CompleteMaintenanceTest(MaintenanceTestCase):
    def test_completion_updates_vehicle_service_state(self):
        order = self._order()
        complete_maintenance(order)

        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.current_odometer_km, Decimal("110200.00"))
        self.assertEqual(self.vehicle.next_service_km, Decimal("120200.00"))
        self.assertEqual(self.vehicle.last_service_date, date.today())
        self.assertEqual(self.vehicle.status, "AVAILABLE")

    def test_completion_marks_the_order_completed(self):
        order = complete_maintenance(self._order())
        self.assertEqual(order.status, "COMPLETED")
        self.assertEqual(order.vehicle.next_service_km, Decimal("120200.00"))

    def test_explicit_next_service_km_overrides_the_interval(self):
        complete_maintenance(self._order(), next_service_km=Decimal("115000.00"))
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.next_service_km, Decimal("115000.00"))

    def test_explicit_zero_next_service_km_is_honoured(self):
        complete_maintenance(self._order(), next_service_km=Decimal("0.00"))
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.next_service_km, Decimal("0.00"))

    def test_completing_twice_is_rejected(self):
        order = complete_maintenance(self._order())
        with self.assertRaises(MaintenanceError):
            complete_maintenance(order)

    def test_odometer_below_current_reading_is_rejected(self):
        order = self._order(odometer_km=Decimal("108000.00"))
        with self.assertRaises(MaintenanceError):
            complete_maintenance(order)

    def test_completed_vehicle_no_longer_raises_an_alert(self):
        from apps.vehicles.services import maintenance_alerts

        self.assertTrue(maintenance_alerts())
        complete_maintenance(self._order())
        self.assertEqual(maintenance_alerts(), [])

    def test_out_of_service_vehicle_is_not_silently_returned_to_service(self):
        self.vehicle.status = "OUT_OF_SERVICE"
        self.vehicle.save(update_fields=["status", "updated_at"])
        complete_maintenance(self._order())
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, "OUT_OF_SERVICE")


class MaintenanceListCompleteButtonTest(MaintenanceTestCase):
    def test_open_order_shows_a_post_form_to_complete(self):
        order = self._order(status="IN_PROGRESS")
        response = self.client.get(reverse("maintenance_list"))
        self.assertContains(response, reverse("maintenance_complete", args=[order.pk]))
        self.assertContains(response, 'method="post"')

    def test_completed_order_does_not_show_the_complete_button(self):
        order = self._order(status="COMPLETED")
        response = self.client.get(reverse("maintenance_list"))
        self.assertNotContains(response, reverse("maintenance_complete", args=[order.pk]))


class MaintenanceCompleteViewTest(MaintenanceTestCase):
    def test_get_does_not_complete_the_order(self):
        order = self._order(status="IN_PROGRESS")
        response = self.client.get(reverse("maintenance_complete", args=[order.pk]))
        self.assertRedirects(response, reverse("maintenance_list"))
        order.refresh_from_db()
        self.assertEqual(order.status, "IN_PROGRESS")

    def test_post_completes_the_order(self):
        order = self._order(status="IN_PROGRESS")
        response = self.client.post(reverse("maintenance_complete", args=[order.pk]))
        self.assertRedirects(response, reverse("maintenance_list"))
        order.refresh_from_db()
        self.assertEqual(order.status, "COMPLETED")
