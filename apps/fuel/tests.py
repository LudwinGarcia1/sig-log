from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.fuel.models import FuelLoad
from apps.fuel.services import efficiency_report
from apps.operators.models import Operator
from apps.vehicles.models import Vehicle


class FuelTestCase(TestCase):
    def setUp(self):
        self.vehicle = Vehicle.objects.create(
            plate="ABC1234", economic_number="EC-0001", brand="Freightliner",
            model="Cascadia", year=date.today().year - 3, vehicle_type="TRUCK",
            cargo_capacity_kg=Decimal("12000.00"), fuel_type="DIESEL",
            tank_capacity_l=Decimal("300.00"), current_odometer_km=Decimal("100000.00"),
            acquisition_date=date.today() - timedelta(days=1000),
            next_service_km=Decimal("110000.00"),
            last_service_date=date.today() - timedelta(days=20),
        )
        self.operator = Operator.objects.create(
            employee_number="OP-0001", first_name="Ana", last_name="Ruiz",
            license_number="LF-99887", license_type="C",
            license_expiry=date.today() + timedelta(days=365),
            hire_date=date.today() - timedelta(days=1200), phone="5512345678",
        )
        self.moment = timezone.now() - timedelta(days=10)

    def _load(self, folio, odometer, liters, offset_days=0):
        return FuelLoad.objects.create(
            folio=folio,
            vehicle=self.vehicle,
            operator=self.operator,
            load_datetime=self.moment + timedelta(days=offset_days),
            station_name="Pemex Toluca Centro",
            liters=Decimal(liters),
            price_per_liter=Decimal("25.00"),
            odometer_km=Decimal(odometer),
        )


class FuelLoadBehaviourTest(FuelTestCase):
    def test_total_cost_is_computed_on_save(self):
        load = self._load("COM-0001", "100000.00", "200.00")
        self.assertEqual(load.total_cost, Decimal("5000.00"))

    def test_first_load_has_no_previous_and_no_efficiency(self):
        load = self._load("COM-0001", "100000.00", "200.00")
        self.assertIsNone(load.previous_load)
        self.assertIsNone(load.km_traveled)
        self.assertIsNone(load.efficiency_km_per_liter)

    def test_second_load_measures_km_against_the_first(self):
        self._load("COM-0001", "100000.00", "200.00")
        second = self._load("COM-0002", "100600.00", "200.00", offset_days=2)
        self.assertEqual(second.km_traveled, Decimal("600.00"))
        self.assertEqual(second.efficiency_km_per_liter, Decimal("3.00"))

    def test_efficiency_is_none_when_odometer_did_not_advance(self):
        self._load("COM-0001", "100000.00", "200.00")
        second = self._load("COM-0002", "100000.00", "200.00", offset_days=2)
        self.assertIsNone(second.efficiency_km_per_liter)


class EfficiencyReportTest(FuelTestCase):
    def test_report_aggregates_by_vehicle(self):
        self._load("COM-0001", "100000.00", "200.00")
        self._load("COM-0002", "100600.00", "200.00", offset_days=2)
        self._load("COM-0003", "101200.00", "200.00", offset_days=4)

        rows = efficiency_report()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["vehicle"], self.vehicle)
        self.assertEqual(row["loads"], 3)
        self.assertEqual(row["liters"], Decimal("600.00"))
        self.assertEqual(row["cost"], Decimal("15000.00"))
        self.assertEqual(row["km"], Decimal("1200.00"))
        self.assertEqual(row["efficiency"], Decimal("3.00"))

    def test_report_is_empty_without_loads(self):
        self.assertEqual(efficiency_report(), [])
