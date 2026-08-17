"""Unidad IV — grouping routes and reducing dimensionality.

PCA does two jobs here: it removes the correlation between distance and
duration, and it makes the result drawable on a plane. K-means then groups the
routes, and every cluster is given a name in Spanish — a cluster without a name
is a number, not extracted knowledge.
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml import datasets

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
CLUSTER_PATH = ARTIFACT_DIR / "route_clusters.joblib"

K_RANGE = range(2, 11)
N_COMPONENTS = 2


def _pipeline(k, random_state):
    """Scale, project to two components, then cluster.

    Scaling first matters: monthly_shipments lives in the tens while
    avg_cargo_kg lives in the thousands, and K-means is distance-based.
    """
    return Pipeline([
        ("scaler", StandardScaler()),
        ("pca", PCA(n_components=N_COMPONENTS, random_state=random_state)),
        ("kmeans", KMeans(n_clusters=k, n_init=25, random_state=random_state)),
    ])


def sweep_k(matrix, k_range=K_RANGE, random_state=42):
    """Elbow plus silhouette plus Davies-Bouldin, for k = 2..10.

    This sweep is the "entrenamiento, prueba y error" the syllabus asks for,
    done with numbers instead of intuition.
    """
    results = []
    for k in k_range:
        pipeline = _pipeline(k, random_state)
        labels = pipeline.fit_predict(matrix)
        projected = pipeline.named_steps["pca"].transform(
            pipeline.named_steps["scaler"].transform(matrix)
        )
        results.append({
            "k": k,
            "inertia": float(pipeline.named_steps["kmeans"].inertia_),
            "silhouette": float(silhouette_score(projected, labels)),
            "davies_bouldin": float(davies_bouldin_score(projected, labels)),
        })
    return results


def choose_k(sweep):
    """Highest silhouette wins; ties break toward the smaller k."""
    best = max(sweep, key=lambda row: (row["silhouette"], -row["k"]))
    return best["k"]


def name_cluster(row):
    """Turn a cluster centroid into a phrase an operations manager can use."""
    long_haul = row["distance_km"] >= 350
    short_haul = row["distance_km"] < 80
    troubled = row["delay_rate"] >= 0.35
    busy = row["monthly_shipments"] >= 20

    if short_haul and troubled:
        return "Rutas urbanas congestionadas"
    if short_haul and busy:
        return "Rutas urbanas de alta frecuencia"
    if long_haul and not troubled:
        return "Rutas foráneas eficientes"
    if long_haul:
        return "Rutas foráneas con retrasos"
    if troubled:
        return "Rutas regionales problemáticas"
    if not busy:
        return "Rutas de bajo volumen"
    return "Rutas regionales estables"


def cluster_routes(profile, k=None, random_state=42):
    """Full Unidad IV run: sweep, choose k, fit, project, name."""
    matrix = profile[datasets.ROUTE_PROFILE_FEATURES]

    sweep = sweep_k(matrix, random_state=random_state)
    chosen = k or choose_k(sweep)

    pipeline = _pipeline(chosen, random_state)
    labels = pipeline.fit_predict(matrix)

    scaled = pipeline.named_steps["scaler"].transform(matrix)
    projected = pipeline.named_steps["pca"].transform(scaled)

    assignments = profile.copy()
    assignments["cluster"] = labels

    summary = (
        assignments.groupby("cluster")[datasets.ROUTE_PROFILE_FEATURES]
        .mean()
        .join(assignments.groupby("cluster").size().rename("routes"))
    )

    labels_by_cluster = {}
    used = set()
    for cluster_id, row in summary.iterrows():
        name = name_cluster(row)
        # Two centroids can land on the same phrase; keep the names distinct.
        if name in used:
            name = f"{name} ({int(row['routes'])} rutas)"
        used.add(name)
        labels_by_cluster[int(cluster_id)] = name

    summary["label"] = [labels_by_cluster[int(i)] for i in summary.index]
    assignments["label"] = [labels_by_cluster[int(value)] for value in labels]

    components = pd.DataFrame(
        projected, columns=["pc1", "pc2"], index=profile.index
    )
    components["cluster"] = labels
    components["label"] = assignments["label"].to_numpy()

    return {
        "k": int(chosen),
        "pipeline": pipeline,
        "sweep": sweep,
        "assignments": assignments,
        "profile_summary": summary,
        "labels_by_cluster": labels_by_cluster,
        "explained_variance": [
            float(value)
            for value in pipeline.named_steps["pca"].explained_variance_ratio_
        ],
        "silhouette": float(silhouette_score(projected, labels)),
        "davies_bouldin": float(davies_bouldin_score(projected, labels)),
        "components": components,
    }


def load_clusters():
    """Load the saved clustering artifact and prepare it for the clusters view.

    Keeps the joblib load and the pandas reshaping out of the view layer,
    which should only orchestrate HTTP concerns (see CrudConfig's layering
    rule in apps/core).
    """
    if not CLUSTER_PATH.exists():
        return None

    artifact = joblib.load(CLUSTER_PATH)
    components = artifact["components"]
    summary = artifact["profile_summary"].reset_index()

    scatter = {}
    for label, group in components.groupby("label"):
        scatter[label] = [
            {"x": round(float(x), 3), "y": round(float(y), 3), "route": index}
            for index, x, y in zip(group.index, group["pc1"], group["pc2"])
        ]

    return {
        "summary": summary.to_dict("records"),
        "scatter": scatter,
    }
