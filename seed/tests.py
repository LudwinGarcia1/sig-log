from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from apps.customers.models import Customer
from apps.deliveries.models import Delivery
from apps.fuel.models import FuelLoad
from apps.maintenance.models import Maintenance
from apps.operators.models import Operator
from apps.routes.models import Route
from apps.vehicles.models import Vehicle
from seed.patterns import CONGESTED_ZONES, PEAK_HOURS, delay_probability


class DelayProbabilityTest(TestCase):
    def test_congested_zone_raises_probability(self):
        clean = delay_probability("NORTE", "FORANEA", 11, 2, 3)
        congested = delay_probability(
            next(iter(CONGESTED_ZONES)), "FORANEA", 11, 2, 3
        )
        self.assertGreater(congested, clean)

    def test_peak_hour_raises_probability(self):
        off_peak = delay_probability("NORTE", "REGIONAL", 11, 2, 3)
        peak = delay_probability("NORTE", "REGIONAL", next(iter(PEAK_HOURS)), 2, 3)
        self.assertGreater(peak, off_peak)

    def test_old_vehicle_raises_probability(self):
        young = delay_probability("NORTE", "REGIONAL", 11, 2, 2)
        old = delay_probability("NORTE", "REGIONAL", 11, 2, 12)
        self.assertGreater(old, young)

    def test_probability_stays_within_bounds(self):
        extreme = delay_probability(
            next(iter(CONGESTED_ZONES)), "LOCAL", next(iter(PEAK_HOURS)), 1, 20
        )
        self.assertLessEqual(extreme, 0.85)
        self.assertGreaterEqual(delay_probability("NORTE", "FORANEA", 3, 6, 0), 0.02)


class SeedCommandTest(TestCase):
    """A short run — three months — to keep the suite fast."""

    @classmethod
    def setUpTestData(cls):
        # seed_demo refuses to run without the delay-cause catalogue.
        call_command("loaddata", "delay_causes", verbosity=0)
        call_command("seed_demo", months=3, seed=42, verbosity=0)

    def test_every_catalogue_is_populated(self):
        self.assertEqual(Customer.objects.count(), 120)
        self.assertEqual(Vehicle.objects.count(), 50)
        self.assertEqual(Operator.objects.count(), 40)
        self.assertEqual(Route.objects.count(), 60)

    def test_transactional_tables_are_populated(self):
        self.assertGreater(Delivery.objects.count(), 1000)
        self.assertGreater(FuelLoad.objects.count(), 300)
        self.assertGreater(Maintenance.objects.count(), 50)

    def test_closed_deliveries_dominate(self):
        closed = Delivery.objects.filter(status__in=["DELIVERED", "DELAYED"]).count()
        self.assertGreater(closed / Delivery.objects.count(), 0.85)

    def test_every_delayed_delivery_states_a_cause(self):
        orphans = Delivery.objects.filter(
            status="DELAYED", delay_cause__isnull=True
        ).count()
        self.assertEqual(orphans, 0)

    def test_delay_rate_is_realistic(self):
        total = Delivery.objects.exclude(actual_arrival__isnull=True).count()
        delayed = Delivery.objects.filter(status="DELAYED").count()
        self.assertGreater(delayed / total, 0.10)
        self.assertLess(delayed / total, 0.50)

    def test_congested_zones_are_measurably_worse(self):
        congested = Delivery.objects.filter(
            route__zone__in=CONGESTED_ZONES, status="DELAYED"
        ).count()
        congested_total = Delivery.objects.filter(
            route__zone__in=CONGESTED_ZONES
        ).exclude(actual_arrival__isnull=True).count()
        clean = Delivery.objects.exclude(route__zone__in=CONGESTED_ZONES).filter(
            status="DELAYED"
        ).count()
        clean_total = Delivery.objects.exclude(
            route__zone__in=CONGESTED_ZONES
        ).exclude(actual_arrival__isnull=True).count()
        self.assertGreater(congested / congested_total, clean / clean_total + 0.10)

    def test_route_archetypes_are_all_present(self):
        self.assertEqual(
            set(Route.objects.values_list("route_type", flat=True).distinct()),
            {"LOCAL", "REGIONAL", "FORANEA"},
        )

    def test_dirty_records_are_injected_for_the_etl_to_catch(self):
        broken_dates = Delivery.objects.filter(
            actual_arrival__lt=models_f_actual_departure()
        ).count()
        self.assertGreater(broken_dates, 0)
        self.assertGreater(FuelLoad.objects.filter(liters__lte=0).count(), 0)

    def test_run_is_reproducible(self):
        first = list(
            Delivery.objects.order_by("folio").values_list("folio", flat=True)[:20]
        )
        call_command("seed_demo", months=3, seed=42, verbosity=0)
        second = list(
            Delivery.objects.order_by("folio").values_list("folio", flat=True)[:20]
        )
        self.assertEqual(first, second)


def models_f_actual_departure():
    from django.db.models import F

    return F("actual_departure")
