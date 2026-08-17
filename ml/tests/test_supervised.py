from django.core.management import call_command
from django.test import TestCase

from ml import datasets, supervised


class SupervisedTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "delay_causes", verbosity=0)
        call_command("seed_demo", months=4, seed=42, verbosity=0)
        call_command("run_etl", rebuild=True, verbosity=0)

    def setUp(self):
        self.frame = datasets.build_delivery_dataset()

    def test_preprocessor_covers_every_declared_feature(self):
        preprocessor = supervised.build_preprocessor()
        covered = set()
        for _, _, columns in preprocessor.transformers:
            covered.update(columns)
        self.assertEqual(covered, set(datasets.FEATURE_COLUMNS))

    def test_classifier_compares_two_candidates(self):
        result = supervised.train_classifier(self.frame)
        names = {candidate["name"] for candidate in result["candidates"]}
        self.assertEqual(names, {"Regresión logística", "Random Forest"})

    def test_classifier_meets_the_f1_threshold(self):
        """Spec success criterion 4: F1 >= 0.75 on the held-out test set."""
        result = supervised.train_classifier(self.frame)
        best = next(
            c for c in result["candidates"] if c["name"] == result["best_name"]
        )
        self.assertGreaterEqual(best["metrics"]["f1"], 0.75)

    def test_classifier_reports_every_required_metric(self):
        result = supervised.train_classifier(self.frame)
        for candidate in result["candidates"]:
            self.assertTrue(
                {"accuracy", "precision", "recall", "f1", "roc_auc"}.issubset(
                    candidate["metrics"]
                )
            )

    def test_confusion_matrix_is_two_by_two(self):
        result = supervised.train_classifier(self.frame)
        self.assertEqual(len(result["confusion_matrix"]), 2)
        self.assertEqual(len(result["confusion_matrix"][0]), 2)

    def test_feature_importances_are_ranked_and_named(self):
        result = supervised.train_classifier(self.frame)
        importances = result["feature_importances"]
        self.assertGreater(len(importances), 5)
        values = [value for _, value in importances]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_zone_or_route_ranks_among_the_top_features(self):
        """The seeded pattern must be the pattern the model actually found."""
        result = supervised.train_classifier(self.frame)
        top = " ".join(name for name, _ in result["feature_importances"][:12])
        self.assertTrue("zone" in top or "route_code" in top)

    def test_regressor_reports_mse_rmse_mae_and_r2(self):
        result = supervised.train_regressor(self.frame)
        self.assertTrue(
            {"mse", "rmse", "mae", "r2"}.issubset(result["metrics"])
        )
        self.assertGreater(result["metrics"]["mse"], 0)
        self.assertGreater(result["metrics"]["mae"], 0)

    def test_regressor_beats_predicting_the_mean(self):
        result = supervised.train_regressor(self.frame)
        self.assertGreater(result["metrics"]["r2"], 0.05)

    def test_pipelines_are_self_contained(self):
        """Scaling and encoding must travel inside the artifact."""
        result = supervised.train_classifier(self.frame)
        self.assertIn("preprocessor", dict(result["best_pipeline"].named_steps))
