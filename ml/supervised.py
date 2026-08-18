"""Unidad III — supervised learning over the delivery fact.

Two questions, two models:

* "¿Llegará tarde?"          -> binary classification
* "¿Cuántos minutos tarde?"  -> linear regression, scored with MSE and MAE

Two classifiers compete so the choice can be justified rather than asserted:
logistic regression gives an interpretable baseline, random forest captures the
route x hour x vehicle-age interactions that were seeded into the data.
"""

from pathlib import Path

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml import datasets

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
CLASSIFIER_PATH = ARTIFACT_DIR / "delay_classifier.joblib"
REGRESSOR_PATH = ARTIFACT_DIR / "delay_regressor.joblib"

TEST_SIZE = 0.20
CV_FOLDS = 5


def build_preprocessor():
    """Scale the numerics, one-hot the categoricals — inside the pipeline.

    Keeping this in the pipeline means the scaler is fitted on training data
    only, and the saved artifact needs no external preprocessing step.
    """
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), datasets.NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                datasets.CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )


def _feature_names(pipeline):
    return list(
        pipeline.named_steps["preprocessor"].get_feature_names_out()
    )


def _classification_metrics(estimator, x_test, y_test):
    predicted = estimator.predict(x_test)
    probabilities = estimator.predict_proba(x_test)[:, 1]
    return {
        "accuracy": float(accuracy_score(y_test, predicted)),
        "precision": float(precision_score(y_test, predicted, zero_division=0)),
        "recall": float(recall_score(y_test, predicted, zero_division=0)),
        "f1": float(f1_score(y_test, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
    }


def train_classifier(frame, random_state=42):
    """Train both candidates, score them, return the winner by F1."""
    features = frame[datasets.FEATURE_COLUMNS]
    target = frame[datasets.CLASSIFICATION_TARGET].astype(int)

    x_train, x_test, y_train, y_test = train_test_split(
        features, target,
        test_size=TEST_SIZE, random_state=random_state, stratify=target,
    )

    specifications = [
        (
            "Regresión logística",
            LogisticRegression(max_iter=2000, random_state=random_state),
        ),
        (
            "Random Forest",
            RandomForestClassifier(
                n_estimators=300,
                min_samples_leaf=3,
                class_weight="balanced_subsample",
                random_state=random_state,
                n_jobs=-1,
            ),
        ),
    ]

    candidates = []
    for name, estimator in specifications:
        pipeline = Pipeline(
            [("preprocessor", build_preprocessor()), ("model", estimator)]
        )
        pipeline.fit(x_train, y_train)
        cv_scores = cross_val_score(
            pipeline, x_train, y_train, cv=CV_FOLDS, scoring="f1", n_jobs=-1
        )
        candidates.append({
            "name": name,
            "pipeline": pipeline,
            "metrics": _classification_metrics(pipeline, x_test, y_test),
            "cv_f1_mean": float(cv_scores.mean()),
            "cv_f1_std": float(cv_scores.std()),
        })

    winner = max(candidates, key=lambda candidate: candidate["metrics"]["f1"])
    best_pipeline = winner["pipeline"]

    names = _feature_names(best_pipeline)
    model = best_pipeline.named_steps["model"]
    if hasattr(model, "feature_importances_"):
        weights = model.feature_importances_
    else:
        weights = np.abs(model.coef_[0])
    importances = sorted(
        zip(names, (float(value) for value in weights)),
        key=lambda pair: pair[1],
        reverse=True,
    )[:25]

    return {
        "best_name": winner["name"],
        "best_pipeline": best_pipeline,
        "candidates": candidates,
        "confusion_matrix": confusion_matrix(
            y_test, best_pipeline.predict(x_test)
        ).tolist(),
        "feature_importances": importances,
        "y_test": y_test,
        "y_pred": best_pipeline.predict(x_test),
        "y_proba": best_pipeline.predict_proba(x_test)[:, 1],
        "test_index": list(x_test.index),
        "train_size": int(len(x_train)),
        "test_size": int(len(x_test)),
    }


def train_regressor(frame, random_state=42):
    """Multiple linear regression on delay minutes, scored with MSE and MAE."""
    features = frame[datasets.FEATURE_COLUMNS]
    target = frame[datasets.REGRESSION_TARGET].astype(float)

    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=TEST_SIZE, random_state=random_state
    )

    pipeline = Pipeline(
        [("preprocessor", build_preprocessor()), ("model", LinearRegression())]
    )
    pipeline.fit(x_train, y_train)
    predicted = pipeline.predict(x_test)

    mse = float(mean_squared_error(y_test, predicted))
    return {
        "pipeline": pipeline,
        "metrics": {
            "mse": mse,
            "rmse": float(np.sqrt(mse)),
            "mae": float(mean_absolute_error(y_test, predicted)),
            "r2": float(r2_score(y_test, predicted)),
        },
        "y_test": y_test,
        "y_pred": predicted,
        "train_size": int(len(x_train)),
        "test_size": int(len(x_test)),
    }


def predict_delay(features):
    """Score one prospective delivery with the saved artifacts.

    ``features`` is a mapping over datasets.FEATURE_COLUMNS. Raises
    FileNotFoundError when the models have not been trained yet, which the view
    turns into a Spanish instruction to run ``train_models``.
    """
    import joblib
    import pandas as pd

    if not CLASSIFIER_PATH.exists() or not REGRESSOR_PATH.exists():
        raise FileNotFoundError(
            "Los modelos no están entrenados. Ejecuta 'python manage.py train_models'."
        )

    row = pd.DataFrame([{column: features[column] for column in datasets.FEATURE_COLUMNS}])
    for column in datasets.CATEGORICAL_FEATURES:
        row[column] = row[column].astype(str)

    classifier = joblib.load(CLASSIFIER_PATH)
    regressor = joblib.load(REGRESSOR_PATH)

    probability = float(classifier.predict_proba(row)[0, 1])
    return {
        "will_be_late": bool(probability >= 0.5),
        "probability": probability,
        "expected_delay_minutes": max(float(regressor.predict(row)[0]), 0.0),
    }
