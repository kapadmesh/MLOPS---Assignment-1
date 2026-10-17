import json
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
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
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

plt.switch_backend("Agg")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "heart_disease.csv"
TRACKING_DIR = PROJECT_ROOT / "mlruns"
TRACKING_URI = f"sqlite:///{(PROJECT_ROOT / 'mlflow.db').as_posix()}"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "stage_03"
STAGE_02_ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "stage_02"
SELECTION_METRIC = "cv_roc_auc_mean"
REGISTERED_MODEL_NAME = "heart-disease-classifier"
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


def load_tuned_parameters(model_name: str) -> dict:
    metrics_path = STAGE_02_ARTIFACT_DIR / model_name / "metrics.json"
    if not metrics_path.exists():
        raise FileNotFoundError(f"Run stage 02 first; missing {metrics_path}")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    return {
        name.removeprefix("classifier__"): value
        for name, value in metrics["best_params"].items()
    }


def select_champion(results: pd.DataFrame) -> pd.Series:
    if results.empty:
        raise ValueError("At least one MLflow run is required for champion selection")
    return results.sort_values(
        [SELECTION_METRIC, "model"], ascending=[False, True],
    ).iloc[0]


def model_alias(model_name: str) -> str:
    return f"model-{model_name.replace('_', '-')}"


def challenger_alias(model_name: str) -> str:
    return f"challenger-{model_name.replace('_', '-')}"


def assign_challenger_alias(client: mlflow.MlflowClient, results: pd.DataFrame) -> None:
    ranked = results.sort_values([SELECTION_METRIC, "model"], ascending=[False, True])
    if len(ranked) > 1:
        client.set_registered_model_alias(
            REGISTERED_MODEL_NAME, "challenger", str(ranked.iloc[1]["model_version"]),
        )
    elif "challenger" in client.get_registered_model(REGISTERED_MODEL_NAME).aliases:
        client.delete_registered_model_alias(REGISTERED_MODEL_NAME, "challenger")


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError("Run stage 01 first")
    TRACKING_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(TRACKING_URI)
    experiment_name = "heart-disease-classification"
    if mlflow.get_experiment_by_name(experiment_name) is None:
        mlflow.create_experiment(experiment_name, artifact_location=TRACKING_DIR.resolve().as_uri())
    experiment = mlflow.set_experiment(experiment_name)

    data = pd.read_csv(DATA_PATH)
    features, target = data[FEATURES], data["target"].astype(int)
    train_features, test_features, train_target, test_target = train_test_split(
        features, target, test_size=0.2, stratify=target, random_state=42,
    )
    cross_validation = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    estimators = {
        "logistic_regression": LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=42,
            **load_tuned_parameters("logistic_regression"),
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300, class_weight="balanced", random_state=42, n_jobs=-1,
            **load_tuned_parameters("random_forest"),
        ),
    }
    scoring = {"accuracy": "accuracy", "precision": "precision", "recall": "recall", "roc_auc": "roc_auc"}
    summaries = []
    for model_name, estimator in estimators.items():
        pipeline = Pipeline([("preprocess", make_preprocessor()), ("classifier", estimator)])
        with mlflow.start_run(run_name=model_name) as run:
            mlflow.set_tags({
                "model_family": model_name,
                "model_name": model_name,
                "dataset": "UCI Cleveland Heart Disease",
                "selection_metric": SELECTION_METRIC,
                "model_status": "candidate",
                "tuning_source": "stage_02",
            })
            mlflow.log_params({
                "model": model_name, "cv_folds": 5, "random_state": 42,
                "test_size": 0.2, **estimator.get_params(),
            })
            scores = cross_validate(
                pipeline, train_features, train_target, cv=cross_validation,
                scoring=scoring, n_jobs=-1,
            )
            means = {
                f"cv_{metric}_mean": float(scores[f"test_{metric}"].mean()) for metric in scoring
            }
            standard_deviations = {
                f"cv_{metric}_std": float(scores[f"test_{metric}"].std()) for metric in scoring
            }
            pipeline.fit(train_features, train_target)
            prediction = pipeline.predict(test_features)
            probability = pipeline.predict_proba(test_features)[:, 1]
            holdout = {
                "test_accuracy": float(accuracy_score(test_target, prediction)),
                "test_precision": float(precision_score(test_target, prediction, zero_division=0)),
                "test_recall": float(recall_score(test_target, prediction, zero_division=0)),
                "test_roc_auc": float(roc_auc_score(test_target, probability)),
            }
            mlflow.log_metrics({**means, **standard_deviations, **holdout})
            with tempfile.TemporaryDirectory() as temporary_directory:
                plot_path = Path(temporary_directory) / "evaluation.png"
                figure, axes = plt.subplots(1, 2, figsize=(10, 4))
                ConfusionMatrixDisplay.from_predictions(
                    test_target, prediction, display_labels=["No disease", "Disease"],
                    ax=axes[0], cmap="Blues",
                )
                RocCurveDisplay.from_predictions(
                    test_target, probability, ax=axes[1], name=model_name,
                )
                axes[1].plot([0, 1], [0, 1], linestyle="--", color="gray")
                figure.tight_layout()
                figure.savefig(plot_path, dpi=160, bbox_inches="tight")
                plt.close(figure)
                mlflow.log_artifact(str(plot_path), artifact_path="evaluation")
            model_info = mlflow.sklearn.log_model(
                pipeline, name="model",
                skops_trusted_types=["numpy.dtype", "sklearn.tree._tree.Tree"],
            )
            registered_version = mlflow.register_model(
                model_uri=model_info.model_uri,
                name=REGISTERED_MODEL_NAME,
                tags={
                    "model_name": model_name,
                    "model_status": "candidate",
                    "source_run_id": run.info.run_id,
                },
            )
            summaries.append({
                "model": model_name,
                "run_id": run.info.run_id,
                "registered_model": REGISTERED_MODEL_NAME,
                "model_version": str(registered_version.version),
                **means, **standard_deviations, **holdout,
            })

    results = pd.DataFrame(summaries).sort_values(
        [SELECTION_METRIC, "model"], ascending=[False, True],
    )
    champion = select_champion(results)
    champion_run_id = str(champion["run_id"])
    champion_version = str(champion["model_version"])
    client = mlflow.MlflowClient()
    try:
        previous_champion = client.get_model_version_by_alias(
            REGISTERED_MODEL_NAME, "champion",
        )
    except mlflow.MlflowException:
        previous_champion = None
    if previous_champion and str(previous_champion.version) != champion_version:
        client.set_model_version_tag(
            REGISTERED_MODEL_NAME, str(previous_champion.version),
            "model_status", "archived",
        )
    for previous in client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string="tags.model_status = 'champion'",
    ):
        if previous.info.run_id != champion_run_id:
            client.set_tag(previous.info.run_id, "model_status", "archived")
            client.set_tag(previous.info.run_id, "model_alias", "archived")
    for rank, row in enumerate(results.itertuples(index=False), start=1):
        status = "champion" if row.run_id == champion_run_id else "challenger"
        primary_alias = "champion" if status == "champion" else challenger_alias(row.model)
        name_alias = model_alias(row.model)
        client.set_tag(row.run_id, "model_status", status)
        client.set_tag(row.run_id, "model_name", row.model)
        client.set_tag(row.run_id, "model_alias", primary_alias)
        client.set_tag(row.run_id, "model_name_alias", name_alias)
        client.set_tag(row.run_id, "selection_rank", str(rank))
        client.set_tag(row.run_id, "selection_metric", SELECTION_METRIC)
        client.set_tag(row.run_id, "selection_value", str(getattr(row, SELECTION_METRIC)))
        client.set_model_version_tag(
            REGISTERED_MODEL_NAME, row.model_version, "model_name", row.model,
        )
        client.set_model_version_tag(
            REGISTERED_MODEL_NAME, row.model_version, "model_status", status,
        )
        client.set_model_version_tag(
            REGISTERED_MODEL_NAME, row.model_version, "source_run_id", row.run_id,
        )
        client.set_model_version_tag(
            REGISTERED_MODEL_NAME, row.model_version, "selection_metric", SELECTION_METRIC,
        )
        client.set_model_version_tag(
            REGISTERED_MODEL_NAME, row.model_version, "selection_value",
            str(getattr(row, SELECTION_METRIC)),
        )
        client.set_registered_model_alias(
            REGISTERED_MODEL_NAME, primary_alias, row.model_version,
        )
        client.set_registered_model_alias(
            REGISTERED_MODEL_NAME, name_alias, row.model_version,
        )
        if status == "champion":
            stale_challenger_alias = challenger_alias(row.model)
            try:
                client.get_model_version_by_alias(REGISTERED_MODEL_NAME, stale_challenger_alias)
            except mlflow.MlflowException:
                pass
            else:
                client.delete_registered_model_alias(
                    REGISTERED_MODEL_NAME, stale_challenger_alias,
                )
    assign_challenger_alias(client, results)
    results["model_status"] = results["run_id"].map(
        lambda run_id: "champion" if run_id == champion_run_id else "challenger"
    )
    results["model_alias"] = results.apply(
        lambda row: "champion"
        if row["run_id"] == champion_run_id
        else challenger_alias(row["model"]),
        axis=1,
    )
    results["model_name_alias"] = results["model"].map(model_alias)
    handoff = {
        "experiment_name": experiment.name,
        "experiment_id": experiment.experiment_id,
        "run_id": champion_run_id,
        "model": str(champion["model"]),
        "model_status": "champion",
        "registered_model": REGISTERED_MODEL_NAME,
        "model_version": champion_version,
        "model_alias": "champion",
        "model_name_alias": model_alias(str(champion["model"])),
        "selection_metric": SELECTION_METRIC,
        "selection_value": float(champion[SELECTION_METRIC]),
    }
    (ARTIFACT_DIR / "champion_run.json").write_text(
        json.dumps(handoff, indent=2), encoding="utf-8",
    )
    (ARTIFACT_DIR / "best_run.json").unlink(missing_ok=True)
    results.to_csv(ARTIFACT_DIR / "mlflow_run_summary.csv", index=False)
    print(json.dumps(handoff, indent=2))
    print(f'mlflow ui --backend-store-uri "{TRACKING_URI}"')


if __name__ == "__main__":
    main()