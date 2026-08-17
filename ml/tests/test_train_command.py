import json

from django.core.management import call_command
from django.test import TestCase

from ml import evaluation, supervised, unsupervised


class TrainModelsCommandTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "delay_causes", verbosity=0)
        call_command("seed_demo", months=4, seed=42, verbosity=0)
        call_command("run_etl", rebuild=True, verbosity=0)

    def setUp(self):
        call_command("train_models", verbosity=0)

    def test_all_three_artifacts_are_written(self):
        self.assertTrue(supervised.CLASSIFIER_PATH.exists())
        self.assertTrue(supervised.REGRESSOR_PATH.exists())
        self.assertTrue(unsupervised.CLUSTER_PATH.exists())

    def test_metrics_file_records_both_units(self):
        payload = json.loads(evaluation.METRICS_PATH.read_text(encoding="utf-8"))
        self.assertIn("classification", payload)
        self.assertIn("regression", payload)
        self.assertIn("clustering", payload)
        self.assertIn("trained_at", payload)

    def test_metrics_include_the_syllabus_measures(self):
        payload = evaluation.load_metrics()
        self.assertIn("mse", payload["regression"]["metrics"])
        self.assertIn("mae", payload["regression"]["metrics"])
        self.assertIn("f1", payload["classification"]["best"]["metrics"])
        self.assertIn("silhouette", payload["clustering"])

    def test_every_diagnostic_figure_is_generated(self):
        for filename in (
            "confusion_matrix.png", "residuals.png",
            "elbow.png", "silhouette.png", "pca_scatter.png",
        ):
            self.assertTrue((evaluation.FIGURE_DIR / filename).exists(), filename)

    def test_saved_classifier_can_score_a_new_delivery(self):
        result = supervised.predict_delay({
            "distance_km": 120.0,
            "planned_duration_min": 120,
            "cargo_weight_kg": 5000.0,
            "packages_count": 40,
            "day_of_week": 1,
            "route_code": "RUT-001",
            "route_type": "LOCAL",
            "zone": "METROPOLITANA",
            "distance_range": "CORTA",
            "time_band": "PICO_AM",
            "vehicle_type": "TRUCK",
            "vehicle_age_range": "9+",
            "operator_seniority_range": "0-2",
            "customer_type": "PREMIUM",
            "is_weekend": "False",
        })
        self.assertIn("will_be_late", result)
        self.assertGreaterEqual(result["probability"], 0.0)
        self.assertLessEqual(result["probability"], 1.0)
        self.assertGreaterEqual(result["expected_delay_minutes"], 0.0)
