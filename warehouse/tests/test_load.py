from django.core.management import call_command
from django.test import TestCase

from warehouse import models as dw
from warehouse.etl.context import EtlRun
from warehouse.etl.extract import run as run_extract
from warehouse.etl.load import run as run_load
from warehouse.etl.transform import run as run_transform


class LoadTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "delay_causes", verbosity=0)
        call_command("seed_demo", months=2, seed=42, verbosity=0)

    def setUp(self):
        self.etl_run = EtlRun(full=True, rebuild=True)
        run_extract(self.etl_run)
        self.counts = run_load(self.etl_run, run_transform(self.etl_run))

    def test_dimensions_are_populated(self):
        self.assertEqual(dw.DimCustomer.objects.count(), 120)
        self.assertEqual(dw.DimVehicle.objects.count(), 50)
        self.assertEqual(dw.DimOperator.objects.count(), 40)
        self.assertEqual(dw.DimRoute.objects.count(), 60)
        self.assertEqual(dw.DimTime.objects.count(), 24)
        self.assertGreater(dw.DimDate.objects.count(), 30)

    def test_facts_are_populated(self):
        self.assertGreater(dw.FactDelivery.objects.count(), 500)
        self.assertGreater(dw.FactFuel.objects.count(), 100)
        self.assertGreater(dw.FactMaintenance.objects.count(), 20)

    def test_every_fact_resolves_its_dimension_keys(self):
        fact = dw.FactDelivery.objects.select_related(
            "date", "time", "customer", "route", "vehicle", "operator"
        ).first()
        self.assertIsNotNone(fact.date_id)
        self.assertIsNotNone(fact.customer.code)
        self.assertIsNotNone(fact.route.code)

    def test_delayed_facts_always_carry_a_cause(self):
        orphans = dw.FactDelivery.objects.filter(
            is_delayed=1, delay_cause__isnull=True
        ).count()
        self.assertEqual(orphans, 0)

    def test_on_time_facts_carry_no_cause(self):
        self.assertEqual(
            dw.FactDelivery.objects.filter(
                is_delayed=0, delay_cause__isnull=False
            ).count(),
            0,
        )

    def test_time_bands_are_assigned(self):
        self.assertEqual(dw.DimTime.objects.get(time_key=8).time_band, "PICO_AM")
        self.assertEqual(dw.DimTime.objects.get(time_key=18).time_band, "PICO_PM")

    def test_load_is_idempotent_on_dimensions(self):
        before = dw.DimCustomer.objects.count()
        second = EtlRun(full=True)
        run_extract(second)
        run_load(second, run_transform(second))
        self.assertEqual(dw.DimCustomer.objects.count(), before)

    def test_load_writes_success_logs(self):
        logs = dw.EtlLog.objects.filter(run_id=self.etl_run.run_id, phase="LOAD")
        self.assertGreaterEqual(logs.count(), 10)
        self.assertTrue(all(log.status == "SUCCESS" for log in logs))


class LoadFailureTest(TestCase):
    """A LOAD phase that raises mid-way must roll back its data but still
    leave a single trace of the failure — see warehouse/etl/load.py."""

    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "delay_causes", verbosity=0)
        call_command("seed_demo", months=2, seed=42, verbosity=0)

    def test_failed_load_rolls_back_but_leaves_one_failed_log(self):
        etl_run = EtlRun(full=True, rebuild=True)
        run_extract(etl_run)
        transformed = run_transform(etl_run)
        # Corrupt one delivery so surrogate-key resolution blows up with a
        # KeyError deep inside the atomic block: the dimension tables are
        # built from the (uncorrupted) rest of the batch, so this code never
        # gets a customer_key.
        transformed["deliveries"][0]["customer_code"] = "NO-SUCH-CUSTOMER"
        before = dw.FactDelivery.objects.count()

        with self.assertRaises(KeyError):
            run_load(etl_run, transformed)

        # The transaction rolled back: no partial fact rows survived.
        self.assertEqual(dw.FactDelivery.objects.count(), before)

        logs = dw.EtlLog.objects.filter(run_id=etl_run.run_id, phase="LOAD")
        self.assertEqual(logs.count(), 1)
        failure_log = logs.first()
        self.assertEqual(failure_log.status, "FAILED")
        self.assertTrue(failure_log.message)

        # The per-table SUCCESS rows rolled back with the data they describe.
        self.assertEqual(logs.filter(status="SUCCESS").count(), 0)


class RunEtlCommandTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "delay_causes", verbosity=0)
        call_command("seed_demo", months=2, seed=42, verbosity=0)

    def test_command_runs_the_three_phases(self):
        call_command("run_etl", full=True, verbosity=0)
        phases = set(dw.EtlLog.objects.values_list("phase", flat=True))
        self.assertEqual(phases, {"EXTRACT", "TRANSFORM", "LOAD"})
        self.assertGreater(dw.FactDelivery.objects.count(), 0)

    def test_rebuild_empties_the_warehouse_first(self):
        call_command("run_etl", full=True, verbosity=0)
        first = dw.FactDelivery.objects.count()
        call_command("run_etl", rebuild=True, verbosity=0)
        self.assertEqual(dw.FactDelivery.objects.count(), first)
