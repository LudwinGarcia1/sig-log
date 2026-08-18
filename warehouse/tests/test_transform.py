from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from warehouse import models as dw
from warehouse.etl.context import EtlRun
from warehouse.etl.extract import run as run_extract
from warehouse.etl.transform import run as run_transform
from warehouse.models import EtlError, EtlLog, StgDelivery


class TransformTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "delay_causes", verbosity=0)
        call_command("seed_demo", months=2, seed=42, verbosity=0)

    def setUp(self):
        self.etl_run = EtlRun(full=True)
        run_extract(self.etl_run)
        self.result = run_transform(self.etl_run)

    def test_every_collection_is_produced(self):
        self.assertEqual(
            set(self.result),
            {
                "customers", "vehicles", "operators", "routes",
                "delay_causes", "deliveries", "fuel_loads", "maintenances",
            },
        )

    def test_customer_cities_are_normalized(self):
        cities = {row["city"] for row in self.result["customers"]}
        self.assertFalse(any(city != city.strip() for city in cities))

    def test_blank_cities_become_desconocida(self):
        self.assertIn("DESCONOCIDA", {row["city"] for row in self.result["customers"]})

    def test_tax_ids_are_uppercased(self):
        self.assertTrue(
            all(row["tax_id"] == row["tax_id"].upper() for row in self.result["customers"])
        )

    def test_incoherent_dates_are_rejected_not_dropped_silently(self):
        rejected = EtlError.objects.filter(
            run_id=self.etl_run.run_id, rule="dates_are_coherent"
        )
        self.assertGreater(rejected.count(), 0)
        self.assertTrue(all(row.raw_payload for row in rejected))

    def test_rejected_deliveries_never_reach_the_clean_set(self):
        rejected_folios = set(
            EtlError.objects.filter(
                run_id=self.etl_run.run_id, source_table="stg_delivery"
            ).values_list("source_pk", flat=True)
        )
        clean_folios = {row["folio"] for row in self.result["deliveries"]}
        self.assertEqual(rejected_folios & clean_folios, set())

    def test_zero_litre_loads_are_rejected(self):
        self.assertGreater(
            EtlError.objects.filter(
                run_id=self.etl_run.run_id, rule="is_positive",
                source_table="stg_fuel_load",
            ).count(),
            0,
        )

    def test_negative_freight_is_rejected(self):
        self.assertGreater(
            EtlError.objects.filter(
                run_id=self.etl_run.run_id, rule="is_non_negative",
                source_table="stg_delivery",
            ).count(),
            0,
        )

    def test_efficiency_outliers_are_quarantined(self):
        self.assertGreater(
            EtlError.objects.filter(
                run_id=self.etl_run.run_id, rule="is_efficiency_outlier"
            ).count(),
            0,
        )

    def test_duplicate_natural_keys_keep_one_row(self):
        codes = [row["code"] for row in self.result["customers"]]
        self.assertEqual(len(codes), len(set(codes)))

    def test_deliveries_carry_derived_columns(self):
        row = self.result["deliveries"][0]
        self.assertTrue(
            {
                "delay_minutes", "is_delayed", "time_key", "date_key",
                "actual_duration_min", "cost_per_km",
            }.issubset(row)
        )

    def test_missing_cause_on_a_late_delivery_becomes_unspecified(self):
        late = [r for r in self.result["deliveries"] if r["is_delayed"] == 1]
        self.assertTrue(all(r["delay_cause_code"] for r in late))

    def test_on_time_delivery_never_carries_a_cause(self):
        on_time = [r for r in self.result["deliveries"] if r["is_delayed"] == 0]
        self.assertGreater(len(on_time), 0)
        self.assertTrue(all(r["delay_cause_code"] is None for r in on_time))

    def test_transform_logs_rejected_counts(self):
        log = EtlLog.objects.get(
            run_id=self.etl_run.run_id, phase="TRANSFORM", table_name="stg_delivery"
        )
        self.assertEqual(log.status, "SUCCESS")
        self.assertGreater(log.rows_rejected, 0)
        self.assertEqual(log.rows_read, StgDelivery.objects.count())


class DelayBoundaryTest(TestCase):
    """Pins DELAY_TOLERANCE_MINUTES = 15 on both sides of the strict '>'
    comparison used by ``apps.deliveries.models.Delivery.is_delayed``.

    A delivery exactly 15 minutes late must NOT be flagged; one minute more
    (16 minutes) must be. Two staged rows, built directly against the
    staging tables, isolate the boundary without depending on the seed
    generator, which never produces an exactly-15/16-minute delay.
    """

    def setUp(self):
        dw.StgCustomer.objects.create(
            code="CLI-0001", business_name="Cliente Uno", tax_id="TAX001",
            city="Toluca", state="Mexico", customer_type="REGULAR",
        )
        dw.StgVehicle.objects.create(
            plate="ABC1234", economic_number="EC-0001", brand="Volvo",
            model="VNL", year=2022, vehicle_type="TRUCK",
            cargo_capacity_kg=Decimal("10000"),
        )
        dw.StgOperator.objects.create(
            employee_number="OP-0001", first_name="Juan", last_name="Perez",
            license_type="C", hire_date=datetime(2020, 1, 1).date(),
        )
        dw.StgRoute.objects.create(
            code="RUT-001", name="Toluca - CDMX", origin_city="Toluca",
            destination_city="CDMX", distance_km=Decimal("60"),
        )

        departure = timezone.make_aware(datetime(2026, 1, 5, 8, 0))
        scheduled_arrival = departure + timedelta(hours=1)

        def _delivery(folio, extra_minutes):
            return dw.StgDelivery.objects.create(
                folio=folio, customer_code="CLI-0001", route_code="RUT-001",
                vehicle_plate="ABC1234", operator_number="OP-0001",
                scheduled_departure=departure, actual_departure=departure,
                scheduled_arrival=scheduled_arrival,
                actual_arrival=scheduled_arrival + timedelta(minutes=extra_minutes),
                cargo_weight_kg=Decimal("500"), packages_count=1,
                freight_cost=Decimal("1000.00"),
            )

        _delivery("ENT-BOUND-15", 15)
        _delivery("ENT-BOUND-16", 16)

    def test_delay_boundary_is_strictly_greater_than_fifteen_minutes(self):
        etl_run = EtlRun(full=True)
        result = run_transform(etl_run)
        deliveries = {row["folio"]: row for row in result["deliveries"]}

        self.assertEqual(deliveries["ENT-BOUND-15"]["delay_minutes"], 15)
        self.assertEqual(deliveries["ENT-BOUND-15"]["is_delayed"], 0)

        self.assertEqual(deliveries["ENT-BOUND-16"]["delay_minutes"], 16)
        self.assertEqual(deliveries["ENT-BOUND-16"]["is_delayed"], 1)


class DeduplicationTest(TestCase):
    """Confirms the ``deduplicate`` rule actually rejects a repeated natural
    key and keeps the newest row.

    seed_demo's dirty-data mix never plants a genuine natural-key duplicate
    for any dimension Transform dedupes (it duplicates a customer's ``tax_id``
    across two distinct ``code`` values, which is a different natural key),
    so ``rule="deduplicate"`` never fires against the seeded dataset. This
    exercises the branch directly so the rule is proven correct even though
    it is not incidentally covered by the generator.
    """

    def test_duplicate_customer_code_keeps_the_newest_and_rejects_the_rest(self):
        dw.StgCustomer.objects.create(
            code="CLI-0001", business_name="Version Antigua", tax_id="TAX001",
            city="Toluca", state="Mexico", customer_type="REGULAR",
        )
        dw.StgCustomer.objects.create(
            code="CLI-0001", business_name="Version Reciente", tax_id="TAX001",
            city="Toluca", state="Mexico", customer_type="REGULAR",
        )

        etl_run = EtlRun(full=True)
        result = run_transform(etl_run)

        matches = [row for row in result["customers"] if row["code"] == "CLI-0001"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["business_name"], "Version Reciente")

        rejected = EtlError.objects.filter(
            run_id=etl_run.run_id, rule="deduplicate", source_table="stg_customer",
        )
        self.assertEqual(rejected.count(), 1)


class FuelOdometerChainTest(TestCase):
    """Confirms the per-vehicle odometer chain advances for EVERY row —
    including one rejected for its own reasons — not just the ones that
    reach the clean set.

    Three loads for one plate; the middle one has ``liters = 0`` and is
    rejected under ``is_positive``. Its odometer reading is still real, so
    the third load's ``km_traveled`` must be measured from the middle
    load's odometer, not from the first load's now two-cycles-old (stale)
    reading — measuring from the stale reading is exactly the bug this
    guards against, since it silently inflates both ``km_traveled`` and
    ``efficiency_km_per_liter`` for every load downstream of a rejection.
    """

    def setUp(self):
        dw.StgVehicle.objects.create(
            plate="FUEL001", economic_number="EC-0009", brand="Kenworth",
            model="T680", year=2020, vehicle_type="TRUCK",
            cargo_capacity_kg=Decimal("12000"),
        )
        dw.StgOperator.objects.create(
            employee_number="OP-0009", first_name="Luis", last_name="Torres",
            license_type="C", hire_date=datetime(2018, 1, 1).date(),
        )

        def _load(folio, day, odometer, liters):
            return dw.StgFuelLoad.objects.create(
                folio=folio, vehicle_plate="FUEL001", operator_number="OP-0009",
                load_datetime=timezone.make_aware(datetime(2026, 1, day, 8, 0)),
                liters=Decimal(liters), price_per_liter=Decimal("25.00"),
                total_cost=Decimal(liters) * Decimal("25.00"),
                odometer_km=Decimal(odometer),
            )

        _load("COM-CHAIN-1", 1, "10000", "100")   # first: no prior reading
        _load("COM-CHAIN-2", 2, "10300", "0")     # middle: rejected, is_positive
        _load("COM-CHAIN-3", 3, "11000", "100")   # third: must chain off #2

    def test_km_traveled_chains_off_the_rejected_rows_real_odometer(self):
        etl_run = EtlRun(full=True)
        result = run_transform(etl_run)

        middle_rejected = EtlError.objects.filter(
            run_id=etl_run.run_id, rule="is_positive",
            source_table="stg_fuel_load", source_pk="COM-CHAIN-2",
        )
        self.assertTrue(middle_rejected.exists())

        clean = {row["folio"]: row for row in result["fuel_loads"]}
        self.assertNotIn("COM-CHAIN-2", clean)

        third = clean["COM-CHAIN-3"]
        self.assertEqual(third["km_traveled"], Decimal("700"))       # 11000 - 10300
        self.assertNotEqual(third["km_traveled"], Decimal("1000"))   # 11000 - 10000 (stale)
        self.assertEqual(third["efficiency_km_per_liter"], Decimal("7.00"))


class ReferentialIntegrityTest(TestCase):
    """Confirms ``referential_integrity`` actually rejects a delivery whose
    ``customer_code`` does not exist among the transformed customers, and
    that the folio never reaches the clean set.

    This guard sits directly upstream of Task 12's surrogate-key resolution:
    a latent bug here would crash the load phase, not merely produce bad
    data, so it deserves a direct positive-firing test rather than relying
    on incidental coverage from the seed generator (which never produces a
    dangling foreign key).
    """

    def test_delivery_with_unknown_customer_is_rejected_and_excluded(self):
        dw.StgVehicle.objects.create(
            plate="XYZ9999", economic_number="EC-0002", brand="Ford",
            model="Transit", year=2021, vehicle_type="VAN",
            cargo_capacity_kg=Decimal("1500"),
        )
        dw.StgOperator.objects.create(
            employee_number="OP-0002", first_name="Ana", last_name="Lopez",
            license_type="B", hire_date=datetime(2019, 1, 1).date(),
        )
        dw.StgRoute.objects.create(
            code="RUT-002", name="Puebla - Queretaro", origin_city="Puebla",
            destination_city="Queretaro", distance_km=Decimal("120"),
        )
        # Deliberately no StgCustomer row exists for "CLI-9999".

        departure = timezone.make_aware(datetime(2026, 2, 1, 9, 0))
        dw.StgDelivery.objects.create(
            folio="ENT-ORPHAN-01", customer_code="CLI-9999", route_code="RUT-002",
            vehicle_plate="XYZ9999", operator_number="OP-0002",
            scheduled_departure=departure, actual_departure=departure,
            scheduled_arrival=departure + timedelta(hours=1),
            actual_arrival=departure + timedelta(hours=1, minutes=5),
            cargo_weight_kg=Decimal("300"), packages_count=1,
            freight_cost=Decimal("500.00"),
        )

        etl_run = EtlRun(full=True)
        result = run_transform(etl_run)

        self.assertNotIn(
            "ENT-ORPHAN-01", {row["folio"] for row in result["deliveries"]}
        )
        self.assertTrue(
            EtlError.objects.filter(
                run_id=etl_run.run_id, rule="referential_integrity",
                source_table="stg_delivery", source_pk="ENT-ORPHAN-01",
            ).exists()
        )
