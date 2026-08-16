from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.customers.models import Customer
from warehouse.etl.context import EtlRun
from warehouse.etl.extract import run as run_extract
from warehouse.models import EtlLog, StgCustomer, StgDelivery, StgRoute


class ExtractTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "delay_causes", verbosity=0)
        call_command("seed_demo", months=2, seed=42, verbosity=0)

    def test_full_extract_lands_every_source_table(self):
        etl_run = EtlRun(full=True)
        counts = run_extract(etl_run)
        self.assertEqual(counts["stg_customer"], Customer.objects.count())
        self.assertGreater(counts["stg_delivery"], 0)
        self.assertEqual(StgRoute.objects.count(), 60)

    def test_full_extract_truncates_previous_landing(self):
        run_extract(EtlRun(full=True))
        first = StgCustomer.objects.count()
        run_extract(EtlRun(full=True))
        self.assertEqual(StgCustomer.objects.count(), first)

    def test_extract_writes_one_log_row_per_table(self):
        etl_run = EtlRun(full=True)
        run_extract(etl_run)
        logs = EtlLog.objects.filter(run_id=etl_run.run_id, phase="EXTRACT")
        self.assertEqual(logs.count(), 8)
        self.assertTrue(all(log.status == "SUCCESS" for log in logs))
        self.assertTrue(all(log.finished_at is not None for log in logs))

    def test_extract_does_not_clean_anything(self):
        """Landing must preserve the source verbatim, dirt included."""
        run_extract(EtlRun(full=True))
        untrimmed = StgCustomer.objects.filter(city__startswith="  ").count()
        self.assertGreater(untrimmed, 0)

    def test_incremental_extract_reads_only_recent_rows(self):
        run_extract(EtlRun(full=True))
        watermark = timezone.now()

        customer = Customer.objects.order_by("code").first()
        customer.business_name = "Razón social modificada"
        customer.save()

        incremental = EtlRun(full=False, since=watermark)
        counts = run_extract(incremental)
        self.assertEqual(counts["stg_customer"], 1)
        self.assertEqual(
            StgCustomer.objects.filter(run_id=incremental.run_id).count(), 1
        )

    def test_last_successful_run_returns_the_latest_finish(self):
        first = EtlRun(full=True)
        run_extract(first)
        # last_successful_run() watches the LOAD phase, not EXTRACT: a run
        # that extracted but never loaded must be re-extracted from scratch.
        EtlLog.objects.filter(run_id=first.run_id).update(
            phase="LOAD", status="SUCCESS"
        )
        self.assertIsNotNone(EtlRun(full=False).last_successful_run())
