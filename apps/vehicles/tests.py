from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from apps.vehicles.models import Vehicle
from apps.vehicles.services import maintenance_alerts


class VehicleFactory:
    counter = 0

    @classmethod
    def build(cls, **overrides):
        cls.counter += 1
        defaults = {
            "plate": f"ABC{cls.counter:04d}",
            "economic_number": f"EC-{cls.counter:04d}",
            "brand": "Freightliner",
            "model": "Cascadia",
            "year": date.today().year - 3,
            "vehicle_type": "TRUCK",
            "cargo_capacity_kg": Decimal("12000.00"),
            "fuel_type": "DIESEL",
            "tank_capacity_l": Decimal("300.00"),
            "current_odometer_km": Decimal("100000.00"),
            "acquisition_date": date.today() - timedelta(days=365 * 3),
            "next_service_km": Decimal("110000.00"),
            "last_service_date": date.today() - timedelta(days=30),
        }
        defaults.update(overrides)
        return Vehicle.objects.create(**defaults)


class VehicleBehaviourTest(TestCase):
    def test_age_years_uses_model_year(self):
        vehicle = VehicleFactory.build(year=date.today().year - 9)
        self.assertEqual(vehicle.age_years, 9)

    def test_age_range_buckets_the_fleet(self):
        self.assertEqual(VehicleFactory.build(year=date.today().year).age_range, "0-3")
        self.assertEqual(
            VehicleFactory.build(year=date.today().year - 6).age_range, "4-8"
        )
        self.assertEqual(
            VehicleFactory.build(year=date.today().year - 12).age_range, "9+"
        )

    def test_km_to_next_service_is_difference(self):
        vehicle = VehicleFactory.build(
            current_odometer_km=Decimal("100000.00"),
            next_service_km=Decimal("110000.00"),
        )
        self.assertEqual(vehicle.km_to_next_service, Decimal("10000.00"))

    def test_needs_maintenance_when_odometer_passed_threshold(self):
        vehicle = VehicleFactory.build(
            current_odometer_km=Decimal("111000.00"),
            next_service_km=Decimal("110000.00"),
        )
        self.assertTrue(vehicle.needs_maintenance)

    def test_needs_maintenance_when_service_is_stale(self):
        vehicle = VehicleFactory.build(
            last_service_date=date.today() - timedelta(days=200)
        )
        self.assertTrue(vehicle.needs_maintenance)

    def test_does_not_need_maintenance_when_recent_and_below_threshold(self):
        self.assertFalse(VehicleFactory.build().needs_maintenance)


class MaintenanceAlertsTest(TestCase):
    def test_alert_reports_overdue_odometer_as_high_severity(self):
        VehicleFactory.build(
            current_odometer_km=Decimal("115000.00"),
            next_service_km=Decimal("110000.00"),
        )
        alerts = maintenance_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], "ALTA")
        self.assertIn("kilometraje", alerts[0]["reason"].lower())

    def test_alert_reports_approaching_service_as_medium_severity(self):
        VehicleFactory.build(
            current_odometer_km=Decimal("109500.00"),
            next_service_km=Decimal("110000.00"),
        )
        alerts = maintenance_alerts()
        self.assertEqual(alerts[0]["severity"], "MEDIA")

    def test_healthy_fleet_produces_no_alerts(self):
        VehicleFactory.build()
        self.assertEqual(maintenance_alerts(), [])

    def test_inactive_vehicles_are_ignored(self):
        vehicle = VehicleFactory.build(
            current_odometer_km=Decimal("115000.00"),
            next_service_km=Decimal("110000.00"),
        )
        vehicle.deactivate()
        self.assertEqual(maintenance_alerts(), [])
