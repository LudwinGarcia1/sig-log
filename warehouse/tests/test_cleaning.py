from datetime import date, datetime, timedelta
from decimal import Decimal

from django.test import SimpleTestCase

from warehouse.etl import cleaning


class NormalizationTest(SimpleTestCase):
    def test_normalize_text_trims_and_collapses_spaces(self):
        self.assertEqual(cleaning.normalize_text("  toluca   centro "), "Toluca Centro")

    def test_normalize_text_handles_none(self):
        self.assertEqual(cleaning.normalize_text(None), "")

    def test_normalize_code_uppercases_and_trims(self):
        self.assertEqual(cleaning.normalize_code("  cli-0001 "), "CLI-0001")

    def test_normalize_plate_strips_separators(self):
        self.assertEqual(cleaning.normalize_plate(" abc-12-34 "), "ABC1234")

    def test_default_if_blank_substitutes_the_fallback(self):
        self.assertEqual(cleaning.default_if_blank("   ", "DESCONOCIDA"), "DESCONOCIDA")
        self.assertEqual(cleaning.default_if_blank(None, "DESCONOCIDA"), "DESCONOCIDA")
        self.assertEqual(cleaning.default_if_blank("Toluca", "DESCONOCIDA"), "Toluca")


class ValidationTest(SimpleTestCase):
    def test_is_positive_rejects_zero_and_none(self):
        self.assertTrue(cleaning.is_positive(Decimal("0.01")))
        self.assertFalse(cleaning.is_positive(Decimal("0.00")))
        self.assertFalse(cleaning.is_positive(Decimal("-5")))
        self.assertFalse(cleaning.is_positive(None))

    def test_is_non_negative_accepts_zero(self):
        self.assertTrue(cleaning.is_non_negative(Decimal("0.00")))
        self.assertFalse(cleaning.is_non_negative(Decimal("-0.01")))

    def test_dates_are_coherent_requires_arrival_after_departure(self):
        departure = datetime(2026, 5, 1, 8, 0)
        self.assertTrue(cleaning.dates_are_coherent(departure, departure + timedelta(hours=2)))
        self.assertFalse(cleaning.dates_are_coherent(departure, departure - timedelta(minutes=1)))

    def test_dates_are_coherent_allows_a_missing_arrival(self):
        self.assertTrue(cleaning.dates_are_coherent(datetime(2026, 5, 1, 8, 0), None))

    def test_efficiency_outliers_fall_outside_the_fleet_band(self):
        self.assertFalse(cleaning.is_efficiency_outlier(Decimal("3.20")))
        self.assertTrue(cleaning.is_efficiency_outlier(Decimal("0.40")))
        self.assertTrue(cleaning.is_efficiency_outlier(Decimal("14.00")))
        self.assertFalse(cleaning.is_efficiency_outlier(None))

    def test_a_healthy_pickup_is_not_an_outlier(self):
        self.assertFalse(cleaning.is_efficiency_outlier(Decimal("8.75")))
        self.assertFalse(cleaning.is_efficiency_outlier(Decimal("11.99")))
        self.assertTrue(cleaning.is_efficiency_outlier(Decimal("12.01")))


class BucketTest(SimpleTestCase):
    def test_age_range_buckets(self):
        self.assertEqual(cleaning.age_range(2024, 2026), "0-3")
        self.assertEqual(cleaning.age_range(2020, 2026), "4-8")
        self.assertEqual(cleaning.age_range(2010, 2026), "9+")

    def test_age_range_boundaries(self):
        self.assertEqual(cleaning.age_range(2023, 2026), "0-3")
        self.assertEqual(cleaning.age_range(2022, 2026), "4-8")
        self.assertEqual(cleaning.age_range(2018, 2026), "4-8")
        self.assertEqual(cleaning.age_range(2017, 2026), "9+")

    def test_distance_range_buckets(self):
        self.assertEqual(cleaning.distance_range(Decimal("30")), "CORTA")
        self.assertEqual(cleaning.distance_range(Decimal("200")), "MEDIA")
        self.assertEqual(cleaning.distance_range(Decimal("700")), "LARGA")

    def test_capacity_range_buckets(self):
        self.assertEqual(cleaning.capacity_range(Decimal("900")), "LIGERA")
        self.assertEqual(cleaning.capacity_range(Decimal("9000")), "MEDIANA")
        self.assertEqual(cleaning.capacity_range(Decimal("22000")), "PESADA")

    def test_seniority_range_buckets(self):
        today = date(2026, 8, 16)
        self.assertEqual(cleaning.seniority_range(date(2026, 1, 1), today), "0-2")
        self.assertEqual(cleaning.seniority_range(date(2021, 1, 1), today), "3-5")
        self.assertEqual(cleaning.seniority_range(date(2012, 1, 1), today), "6+")
