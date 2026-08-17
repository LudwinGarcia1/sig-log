"""Train every model, save the artifacts, render the diagnostic figures."""

import joblib
from django.core.management.base import BaseCommand
from django.utils import timezone

from ml import datasets, evaluation, supervised, unsupervised


class Command(BaseCommand):
    help = (
        "Entrena los modelos supervisados y no supervisados a partir del "
        "data warehouse, guarda los artefactos y genera las gráficas."
    )

    def add_arguments(self, parser):
        parser.add_argument("--random-state", type=int, default=42)
        parser.add_argument(
            "--k", type=int, default=None,
            help="Fuerza el número de conglomerados en lugar de elegirlo por silueta.",
        )

    def handle(self, *args, **options):
        verbose = options["verbosity"] > 0
        random_state = options["random_state"]

        frame = datasets.build_delivery_dataset()
        if frame.empty:
            self.stderr.write(self.style.ERROR(
                "El data warehouse está vacío. Ejecuta 'python manage.py run_etl --rebuild'."
            ))
            return

        if verbose:
            self.stdout.write(f"Entrenando sobre {len(frame)} entregas…")

        classification = supervised.train_classifier(frame, random_state)
        regression = supervised.train_regressor(frame, random_state)
        profile = datasets.build_route_profile()
        clustering = unsupervised.cluster_routes(
            profile, k=options["k"], random_state=random_state
        )

        supervised.ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(classification["best_pipeline"], supervised.CLASSIFIER_PATH)
        joblib.dump(regression["pipeline"], supervised.REGRESSOR_PATH)
        joblib.dump(
            {
                "pipeline": clustering["pipeline"],
                "labels_by_cluster": clustering["labels_by_cluster"],
                "assignments": clustering["assignments"][["cluster", "label"]],
                "components": clustering["components"],
                "profile_summary": clustering["profile_summary"],
            },
            unsupervised.CLUSTER_PATH,
        )

        evaluation.plot_confusion_matrix(classification["confusion_matrix"])
        evaluation.plot_residuals(regression["y_test"], regression["y_pred"])
        evaluation.plot_elbow(clustering["sweep"])
        evaluation.plot_silhouette(clustering["sweep"])
        evaluation.plot_pca_scatter(clustering["components"])

        evaluation.save_metrics({
            "trained_at": timezone.now().isoformat(),
            "rows": int(len(frame)),
            "classification": {
                "best_name": classification["best_name"],
                "best": {
                    "name": classification["best_name"],
                    "metrics": next(
                        c["metrics"] for c in classification["candidates"]
                        if c["name"] == classification["best_name"]
                    ),
                },
                "candidates": [
                    {
                        "name": candidate["name"],
                        "metrics": candidate["metrics"],
                        "cv_f1_mean": candidate["cv_f1_mean"],
                        "cv_f1_std": candidate["cv_f1_std"],
                    }
                    for candidate in classification["candidates"]
                ],
                "confusion_matrix": classification["confusion_matrix"],
                "feature_importances": classification["feature_importances"],
                "train_size": classification["train_size"],
                "test_size": classification["test_size"],
            },
            "regression": {
                "metrics": regression["metrics"],
                "train_size": regression["train_size"],
                "test_size": regression["test_size"],
            },
            "clustering": {
                "k": clustering["k"],
                "silhouette": clustering["silhouette"],
                "davies_bouldin": clustering["davies_bouldin"],
                "explained_variance": clustering["explained_variance"],
                "sweep": clustering["sweep"],
                "labels": clustering["labels_by_cluster"],
                "summary": clustering["profile_summary"].reset_index().to_dict("records"),
            },
        })

        if verbose:
            best = next(
                c for c in classification["candidates"]
                if c["name"] == classification["best_name"]
            )
            self.stdout.write(self.style.SUCCESS(
                f"Clasificación · ganador: {classification['best_name']} "
                f"(F1 {best['metrics']['f1']:.3f}, "
                f"exactitud {best['metrics']['accuracy']:.3f})"
            ))
            self.stdout.write(self.style.SUCCESS(
                f"Regresión · MSE {regression['metrics']['mse']:.2f} · "
                f"MAE {regression['metrics']['mae']:.2f} · "
                f"R² {regression['metrics']['r2']:.3f}"
            ))
            self.stdout.write(self.style.SUCCESS(
                f"Agrupamiento · k={clustering['k']} · "
                f"silueta {clustering['silhouette']:.3f} · "
                f"varianza explicada {sum(clustering['explained_variance']):.1%}"
            ))
