"""Diagnostic figures and the persisted metrics report.

matplotlib is the right tool for model diagnostics, and Unidad V asks for
matplotlib code in the repository. Chart.js handles the business dashboard;
these five figures handle the models.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")            # headless: no display server in a web process
import matplotlib.pyplot as plt  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
FIGURE_DIR = BASE_DIR / "static" / "ml"
METRICS_PATH = Path(__file__).resolve().parent / "artifacts" / "metrics.json"

FIGURE_DIR.mkdir(parents=True, exist_ok=True)
PALETTE = ["#0d6efd", "#dc3545", "#198754", "#fd7e14", "#6f42c1",
           "#20c997", "#d63384", "#6c757d", "#ffc107", "#0dcaf0"]


def _save(figure, path):
    figure.tight_layout()
    figure.savefig(path, dpi=120)
    plt.close(figure)
    return path


def plot_confusion_matrix(matrix, path=None):
    path = path or FIGURE_DIR / "confusion_matrix.png"
    figure, axes = plt.subplots(figsize=(4.6, 4.2))
    axes.imshow(matrix, cmap="Blues")
    labels = ["A tiempo", "Con retraso"]
    axes.set_xticks([0, 1], labels)
    axes.set_yticks([0, 1], labels)
    axes.set_xlabel("Predicción")
    axes.set_ylabel("Valor real")
    axes.set_title("Matriz de confusión")
    total = sum(sum(row) for row in matrix)
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            axes.text(
                j, i, f"{value}\n{value / total:.1%}",
                ha="center", va="center",
                color="white" if value > total * 0.25 else "black",
            )
    return _save(figure, path)


def plot_residuals(y_test, y_pred, path=None):
    path = path or FIGURE_DIR / "residuals.png"
    residuals = [actual - predicted for actual, predicted in zip(y_test, y_pred)]
    figure, axes = plt.subplots(figsize=(6.2, 4.2))
    axes.scatter(y_pred, residuals, s=8, alpha=0.35, color=PALETTE[0])
    axes.axhline(0, color=PALETTE[1], linewidth=1.2)
    axes.set_xlabel("Minutos de retraso predichos")
    axes.set_ylabel("Residual (real − predicho)")
    axes.set_title("Residuales de la regresión lineal")
    return _save(figure, path)


def plot_elbow(sweep, path=None):
    path = path or FIGURE_DIR / "elbow.png"
    figure, axes = plt.subplots(figsize=(6.0, 4.0))
    axes.plot(
        [row["k"] for row in sweep], [row["inertia"] for row in sweep],
        marker="o", color=PALETTE[0],
    )
    axes.set_xlabel("Número de conglomerados (k)")
    axes.set_ylabel("Inercia")
    axes.set_title("Método del codo")
    axes.grid(alpha=0.25)
    return _save(figure, path)


def plot_silhouette(sweep, path=None):
    path = path or FIGURE_DIR / "silhouette.png"
    figure, axes = plt.subplots(figsize=(6.0, 4.0))
    axes.plot(
        [row["k"] for row in sweep], [row["silhouette"] for row in sweep],
        marker="o", color=PALETTE[2],
    )
    axes.axhline(0.40, color=PALETTE[1], linestyle="--", linewidth=1,
                 label="Umbral objetivo 0.40")
    axes.set_xlabel("Número de conglomerados (k)")
    axes.set_ylabel("Coeficiente de silueta")
    axes.set_title("Silueta por número de conglomerados")
    axes.legend()
    axes.grid(alpha=0.25)
    return _save(figure, path)


def plot_pca_scatter(components, path=None):
    path = path or FIGURE_DIR / "pca_scatter.png"
    figure, axes = plt.subplots(figsize=(6.6, 5.0))
    for index, (label, group) in enumerate(components.groupby("label")):
        axes.scatter(
            group["pc1"], group["pc2"], s=55, alpha=0.85,
            color=PALETTE[index % len(PALETTE)], label=label,
        )
    axes.set_xlabel("Componente principal 1")
    axes.set_ylabel("Componente principal 2")
    axes.set_title("Conglomerados de rutas en el plano PCA")
    axes.legend(fontsize=8, loc="best")
    axes.grid(alpha=0.2)
    return _save(figure, path)


def save_metrics(payload):
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return METRICS_PATH


def load_metrics():
    if not METRICS_PATH.exists():
        return {}
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
