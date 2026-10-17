import json
from importlib.metadata import version
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRACKING_URI = f"sqlite:///{(PROJECT_ROOT / 'mlflow.db').as_posix()}"
CHAMPION_RUN_PATH = PROJECT_ROOT / "artifacts" / "stage_03" / "champion_run.json"
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "heart_disease.csv"
MODEL_DIR = PROJECT_ROOT / "models"
FEATURES = [
    "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
    "thalach", "exang", "oldpeak", "slope", "ca", "thal",
]
DEPENDENCIES = [
    "joblib", "matplotlib", "mlflow", "numpy", "pandas", "requests", "scikit-learn", "seaborn",
]
FINAL_CHAMPION_ALIAS = "final-champion"


def promote_final_champion(
    client: mlflow.MlflowClient, registered_model: str, model_version: str,
) -> None:
    selected = client.get_model_version(registered_model, model_version)
    if selected.tags.get("model_status") != "champion":
        raise ValueError("Only a champion model version can become final-champion")
    previous_version = client.get_registered_model(registered_model).aliases.get(
        FINAL_CHAMPION_ALIAS,
    )
    client.set_registered_model_alias(registered_model, FINAL_CHAMPION_ALIAS, model_version)
    client.set_model_version_tag(
        registered_model, model_version, "packaging_status", FINAL_CHAMPION_ALIAS,
    )
    client.set_tag(selected.run_id, "packaging_status", FINAL_CHAMPION_ALIAS)
    if previous_version is not None and str(previous_version) != model_version:
        previous = client.get_model_version(registered_model, str(previous_version))
        client.set_model_version_tag(
            registered_model, str(previous_version), "packaging_status", "archived",
        )
        client.set_tag(previous.run_id, "packaging_status", "archived")


def main() -> None:
    if not CHAMPION_RUN_PATH.exists():
        raise FileNotFoundError("Run stage 03 first to create the champion-run handoff")
    if not DATA_PATH.exists():
        raise FileNotFoundError("Run stage 01 first to create the cleaned dataset")
    champion_run = json.loads(CHAMPION_RUN_PATH.read_text(encoding="utf-8"))
    if champion_run.get("model_status") != "champion":
        raise ValueError("Stage 03 handoff is not marked as champion")
    mlflow.set_tracking_uri(TRACKING_URI)
    client = mlflow.MlflowClient()
    tracked_run = mlflow.get_run(champion_run["run_id"])
    if tracked_run.data.tags.get("model_status") != "champion":
        raise ValueError("The selected MLflow run is not tagged as champion")
    registered_model = champion_run["registered_model"]
    model_alias = champion_run.get("model_alias")
    if model_alias != "champion":
        raise ValueError("Stage 03 handoff must select the champion model alias")
    aliased_version = client.get_model_version_by_alias(registered_model, model_alias)
    if (
        str(aliased_version.version) != str(champion_run["model_version"])
        or aliased_version.run_id != champion_run["run_id"]
    ):
        raise ValueError("The champion alias does not match the stage 03 handoff")
    name_alias = champion_run["model_name_alias"]
    named_version = client.get_model_version_by_alias(registered_model, name_alias)
    if str(named_version.version) != str(aliased_version.version):
        raise ValueError("The model-name alias does not match the champion version")
    if (
        aliased_version.tags.get("model_status") != "champion"
        or aliased_version.tags.get("model_name") != champion_run["model"]
    ):
        raise ValueError("The champion version has inconsistent status or model-name tags")
    model_uri = f"models:/{registered_model}/{aliased_version.version}"
    model = mlflow.sklearn.load_model(model_uri)

    sample = pd.read_csv(DATA_PATH)[FEATURES].iloc[[0]].copy()
    prediction = int(model.predict(sample)[0])
    probabilities = model.predict_proba(sample)[0]
    if prediction not in (0, 1) or not np.isclose(probabilities.sum(), 1.0):
        raise RuntimeError("Selected model failed the inference smoke test")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / "heart_disease_pipeline.joblib"
    metadata_path = MODEL_DIR / "model_metadata.json"
    joblib.dump(model, model_path)
    if joblib.load(model_path).predict(sample).tolist() != [prediction]:
        raise RuntimeError("Packaged model failed the reload test")
    metadata = {
        "model_name": champion_run["model"],
        "model_status": "champion",
        "registered_model": registered_model,
        "model_version": str(aliased_version.version),
        "model_alias": model_alias,
        "model_name_alias": name_alias,
        "final_model_alias": FINAL_CHAMPION_ALIAS,
        "packaging_status": FINAL_CHAMPION_ALIAS,
        "mlflow_run_id": champion_run["run_id"],
        "selection_metric": champion_run["selection_metric"],
        "selection_value": champion_run["selection_value"],
        "target_mapping": {"0": "no disease", "1": "disease present (original num 1-4)"},
        "features": FEATURES,
        "categorical_features": ["sex", "cp", "fbs", "restecg", "exang", "slope", "ca", "thal"],
        "warning": "Educational model only; not for diagnosis or clinical decision-making.",
    }
    requirements = [f"{package}=={version(package)}" for package in DEPENDENCIES]
    (PROJECT_ROOT / "requirements.txt").write_text(
        "\n".join(requirements) + "\n", encoding="utf-8",
    )
    promote_final_champion(client, registered_model, str(aliased_version.version))
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({
        "model": str(model_path),
        "metadata": str(metadata_path),
        "prediction": prediction,
        "confidence": float(np.max(probabilities)),
    }, indent=2))


if __name__ == "__main__":
    main()