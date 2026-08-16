from django.core.management import call_command
from django.test import TestCase

from ml import datasets


class FeatureContractTest(TestCase):
    """These assertions are the whole reason this module exists."""

    def test_no_feature_is_a_leakage_column(self):
        self.assertEqual(
            set(datasets.FEATURE_COLUMNS) & set(datasets.LEAKAGE_COLUMNS), set()
        )

    def test_leakage_list_names_the_post_hoc_columns(self):
        self.assertTrue(
            {
                "actual_departure", "actual_arrival", "status", "delay_cause",
                "delay_cause_code", "actual_duration_min", "delay_minutes",
                "is_delayed",
            }.issubset(datasets.LEAKAGE_COLUMNS)
        )

    def test_targets_are_not_features(self):
        self.assertNotIn(datasets.CLASSIFICATION_TARGET, datasets.FEATURE_COLUMNS)
        self.assertNotIn(datasets.REGRESSION_TARGET, datasets.FEATURE_COLUMNS)

    def test_route_identity_is_a_feature(self):
        """Congestion is seeded per zone and per route; both must be visible."""
        self.assertIn("route_code", datasets.FEATURE_COLUMNS)
        self.assertIn("zone", datasets.FEATURE_COLUMNS)

    def test_feature_columns_is_numeric_plus_categorical(self):
        self.assertEqual(
            set(datasets.FEATURE_COLUMNS),
            set(datasets.NUMERIC_FEATURES) | set(datasets.CATEGORICAL_FEATURES),
        )


class DatasetBuildTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "delay_causes", verbosity=0)
        call_command("seed_demo", months=3, seed=42, verbosity=0)
        call_command("run_etl", rebuild=True, verbosity=0)

    def test_delivery_dataset_has_rows_and_both_targets(self):
        frame = datasets.build_delivery_dataset()
        self.assertGreater(len(frame), 500)
        self.assertIn(datasets.CLASSIFICATION_TARGET, frame.columns)
        self.assertIn(datasets.REGRESSION_TARGET, frame.columns)

    def test_delivery_dataset_exposes_exactly_the_declared_features(self):
        frame = datasets.build_delivery_dataset()
        for column in datasets.FEATURE_COLUMNS:
            self.assertIn(column, frame.columns)

    def test_delivery_dataset_has_no_nulls_in_features(self):
        frame = datasets.build_delivery_dataset()
        self.assertEqual(int(frame[datasets.FEATURE_COLUMNS].isna().sum().sum()), 0)

    def test_both_classes_are_present(self):
        frame = datasets.build_delivery_dataset()
        self.assertEqual(set(frame[datasets.CLASSIFICATION_TARGET].unique()), {0, 1})

    def test_route_profile_has_one_row_per_route(self):
        profile = datasets.build_route_profile()
        self.assertEqual(len(profile), 60)
        self.assertEqual(profile.index.name, "route_code")

    def test_route_profile_exposes_the_declared_features(self):
        profile = datasets.build_route_profile()
        for column in datasets.ROUTE_PROFILE_FEATURES:
            self.assertIn(column, profile.columns)

    def test_route_profile_has_no_nulls(self):
        profile = datasets.build_route_profile()
        self.assertEqual(
            int(profile[datasets.ROUTE_PROFILE_FEATURES].isna().sum().sum()), 0
        )
