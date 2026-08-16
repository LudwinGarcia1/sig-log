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
                run_id=self.etl_run.run_id, rule="is_positive"
            ).count(),
            0,
        )

    def test_negative_freight_is_rejected(self):
        self.assertGreater(
            EtlError.objects.filter(
                run_id=self.etl_run.run_id, rule="is_non_negative"
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
