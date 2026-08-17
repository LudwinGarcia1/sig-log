from django.core.management import call_command
from django.test import TestCase

from ml import datasets, unsupervised


class UnsupervisedTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "delay_causes", verbosity=0)
        call_command("seed_demo", months=4, seed=42, verbosity=0)
        call_command("run_etl", rebuild=True, verbosity=0)

    def setUp(self):
        self.profile = datasets.build_route_profile()

    def test_sweep_covers_k_two_through_ten(self):
        sweep = unsupervised.sweep_k(
            self.profile[datasets.ROUTE_PROFILE_FEATURES]
        )
        self.assertEqual([row["k"] for row in sweep], list(range(2, 11)))

    def test_sweep_reports_all_three_metrics(self):
        sweep = unsupervised.sweep_k(
            self.profile[datasets.ROUTE_PROFILE_FEATURES]
        )
        for row in sweep:
            self.assertIn("inertia", row)
            self.assertIn("silhouette", row)
            self.assertIn("davies_bouldin", row)

    def test_inertia_decreases_monotonically(self):
        sweep = unsupervised.sweep_k(
            self.profile[datasets.ROUTE_PROFILE_FEATURES]
        )
        inertias = [row["inertia"] for row in sweep]
        self.assertEqual(inertias, sorted(inertias, reverse=True))

    def test_choose_k_picks_the_best_silhouette(self):
        sweep = [
            {"k": 2, "inertia": 100.0, "silhouette": 0.50, "davies_bouldin": 0.6},
            {"k": 3, "inertia": 50.0, "silhouette": 0.70, "davies_bouldin": 0.5},
            {"k": 4, "inertia": 20.0, "silhouette": 0.65, "davies_bouldin": 0.4},
        ]
        self.assertEqual(unsupervised.choose_k(sweep), 3)

    def test_choose_k_breaks_a_silhouette_tie_toward_the_smaller_k(self):
        """A tie in silhouette must not be resolved arbitrarily by dict/list
        order — the real sweep ties this closely (0.73812 vs 0.73800) and
        docs/U4 justifies k=3 on the assumption that ties favour the
        smaller k."""
        sweep = [
            {"k": 2, "inertia": 100.0, "silhouette": 0.50, "davies_bouldin": 0.6},
            {"k": 3, "inertia": 50.0, "silhouette": 0.73812, "davies_bouldin": 0.5},
            {"k": 4, "inertia": 20.0, "silhouette": 0.73812, "davies_bouldin": 0.4},
        ]
        self.assertEqual(unsupervised.choose_k(sweep), 3)

    def test_clustering_meets_the_silhouette_threshold(self):
        """Spec success criterion 5: silhouette >= 0.40."""
        result = unsupervised.cluster_routes(self.profile)
        self.assertGreaterEqual(result["silhouette"], 0.40)

    def test_pca_reduces_to_two_components(self):
        result = unsupervised.cluster_routes(self.profile)
        self.assertEqual(len(result["explained_variance"]), 2)
        self.assertGreater(sum(result["explained_variance"]), 0.55)

    def test_every_route_receives_a_cluster(self):
        result = unsupervised.cluster_routes(self.profile)
        self.assertEqual(len(result["assignments"]), len(self.profile))
        self.assertFalse(result["assignments"]["cluster"].isna().any())

    def test_components_frame_carries_pc1_and_pc2_per_route(self):
        result = unsupervised.cluster_routes(self.profile)
        self.assertEqual(
            set(result["components"].columns), {"pc1", "pc2", "cluster", "label"}
        )
        self.assertEqual(len(result["components"]), len(self.profile))

    def test_every_cluster_gets_an_interpretable_spanish_label(self):
        result = unsupervised.cluster_routes(self.profile)
        labels = set(result["labels_by_cluster"].values())
        self.assertEqual(len(labels), result["k"])
        self.assertTrue(all(label and label[0].isupper() for label in labels))
        self.assertFalse(any(label.isdigit() for label in labels))

    def test_profile_summary_has_one_row_per_cluster(self):
        result = unsupervised.cluster_routes(self.profile)
        self.assertEqual(len(result["profile_summary"]), result["k"])
        self.assertIn("routes", result["profile_summary"].columns)
