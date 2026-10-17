import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    accuracy_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

plt.switch_backend("Agg")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "heart_disease.csv"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "stage_02"
NUMERIC_FEATURES = ["age", "trestbps", "chol", "thalach", "oldpeak"]
CATEGORICAL_FEATURES = ["sex", "cp", "fbs", "restecg", "exang", "slope", "ca", "thal"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def make_preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("numeric", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]), NUMERIC_FEATURES),
        ("categorical", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), CATEGORICAL_FEATURES),
    ])


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError("Run stage 01 first")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(DATA_PATH)
    features, target = data[FEATURES], data["target"].astype(int)
    train_features, test_features, train_target, test_target = train_test_split(
        features, target, test_size=0.2, stratify=target, random_state=42,
    )
    estimators = {
        "logistic_regression": LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=42,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300, class_weight="balanced", random_state=42, n_jobs=-1,
        ),
    }
    pipelines = {
        name: Pipeline([("preprocess", make_preprocessor()), ("classifier", estimator)])
        for name, estimator in estimators.items()
    }
    cross_validation = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = {"accuracy": "accuracy", "precision": "precision", "recall": "recall", "roc_auc": "roc_auc"}
    rows = []
    for name, pipeline in pipelines.items():
        scores = cross_validate(
            pipeline, train_features, train_target, cv=cross_validation, scoring=scoring, n_jobs=-1,
        )
        row = {"model": name}
        for metric in scoring:
            row[f"{metric}_mean"] = float(scores[f"test_{metric}"].mean())
            row[f"{metric}_std"] = float(scores[f"test_{metric}"].std())
        rows.append(row)
    pd.DataFrame(rows).sort_values("roc_auc_mean", ascending=False).to_csv(
        ARTIFACT_DIR / "baseline_cv_results.csv", index=False,
    )

    search_spaces = {
        "logistic_regression": {
            "classifier__C": [0.1, 1.0, 10.0],
            "classifier__solver": ["liblinear", "lbfgs"],
        },
        "random_forest": {
            "classifier__max_depth": [None, 4, 8],
            "classifier__min_samples_leaf": [1, 3, 5],
        },
    }
    searches = {}
    for name, pipeline in pipelines.items():
        search = GridSearchCV(
            pipeline, search_spaces[name], scoring="roc_auc", cv=cross_validation, n_jobs=-1, refit=True,
        )
        search.fit(train_features, train_target)
        searches[name] = search
    best_name = max(searches, key=lambda name: searches[name].best_score_)
    model_results = []
    for name, search in searches.items():
        model = search.best_estimator_
        prediction = model.predict(test_features)
        probability = model.predict_proba(test_features)[:, 1]
        metrics = {
            "model": name,
            "selected_for_stage_02": name == best_name,
            "selection_metric": "cv_roc_auc",
            "best_cv_roc_auc": float(search.best_score_),
            "best_params": search.best_params_,
            "test_accuracy": float(accuracy_score(test_target, prediction)),
            "test_precision": float(precision_score(test_target, prediction, zero_division=0)),
            "test_recall": float(recall_score(test_target, prediction, zero_division=0)),
            "test_roc_auc": float(roc_auc_score(test_target, probability)),
        }
        model_results.append(metrics)
        model_directory = ARTIFACT_DIR / name
        model_directory.mkdir(parents=True, exist_ok=True)
        (model_directory / "metrics.json").write_text(
            json.dumps(metrics, indent=2), encoding="utf-8",
        )
        joblib.dump(model, model_directory / "model.joblib")

        figure, axes = plt.subplots(1, 2, figsize=(11, 4))
        ConfusionMatrixDisplay.from_predictions(
            test_target, prediction, display_labels=["No disease", "Disease"],
            ax=axes[0], cmap="Blues",
        )
        axes[0].set_title(f"{name}: confusion matrix")
        RocCurveDisplay.from_predictions(test_target, probability, ax=axes[1], name=name)
        axes[1].plot([0, 1], [0, 1], linestyle="--", color="gray")
        axes[1].set_title(f"{name}: ROC curve")
        figure.tight_layout()
        figure.savefig(
            model_directory / "holdout_evaluation.png", dpi=160, bbox_inches="tight",
        )
        plt.close(figure)

    comparison = pd.DataFrame(model_results).sort_values(
        ["best_cv_roc_auc", "model"], ascending=[False, True],
    )
    comparison.to_csv(ARTIFACT_DIR / "tuned_model_results.csv", index=False)
    selection = {
        "selected_model": best_name,
        "selection_metric": "best_cv_roc_auc",
        "selection_value": float(searches[best_name].best_score_),
        "note": "Stage 03 independently tracks both models and assigns the MLflow champion tag.",
    }
    (ARTIFACT_DIR / "selection.json").write_text(
        json.dumps(selection, indent=2), encoding="utf-8",
    )
    for legacy_name in ["evaluation.json", "development_model.joblib", "holdout_evaluation.png"]:
        (ARTIFACT_DIR / legacy_name).unlink(missing_ok=True)
    print(comparison.to_string(index=False))
    print(json.dumps(selection, indent=2))


if __name__ == "__main__":
    main()