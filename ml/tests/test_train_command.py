import json
import tempfile
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from ml import evaluation, supervised, unsupervised


class TrainModelsCommandTest(TestCase):
    """Runs the real training command, but every artifact and figure lands
    in a scratch directory instead of ml/artifacts/ and static/ml/ — those
    hold the production models (trained on the full 26,886-delivery
    warehouse) and must never be overwritten by the test suite."""

    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "delay_causes", verbosity=0)
        call_command("seed_demo", months=4, seed=42, verbosity=0)
        call_command("run_etl", rebuild=True, verbosity=0)

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(self._tmp_dir.name)
        artifact_dir = tmp_path / "artifacts"
        figure_dir = tmp_path / "static_ml"

        self.classifier_path = artifact_dir / "delay_classifier.joblib"
        self.regressor_path = artifact_dir / "delay_regressor.joblib"
        self.cluster_path = artifact_dir / "route_clusters.joblib"
        self.metrics_path = artifact_dir / "metrics.json"
        self.figure_dir = figure_dir

        patches = [
            mock.patch.object(supervised, "ARTIFACT_DIR", artifact_dir),
            mock.patch.object(supervised, "CLASSIFIER_PATH", self.classifier_path),
            mock.patch.object(supervised, "REGRESSOR_PATH", self.regressor_path),
            mock.patch.object(unsupervised, "CLUSTER_PATH", self.cluster_path),
            mock.patch.object(evaluation, "FIGURE_DIR", self.figure_dir),
            mock.patch.object(evaluation, "METRICS_PATH", self.metrics_path),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp_dir.cleanup)

        call_command("train_models", verbosity=0)

    def test_all_three_artifacts_are_written(self):
        self.assertTrue(self.classifier_path.exists())
        self.assertTrue(self.regressor_path.exists())
        self.assertTrue(self.cluster_path.exists())

    def test_metrics_file_records_both_units(self):
        payload = json.loads(self.metrics_path.read_text(encoding="utf-8"))
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
            self.assertTrue((self.figure_dir / filename).exists(), filename)

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
