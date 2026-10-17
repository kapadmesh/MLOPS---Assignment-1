import argparse
from importlib.metadata import version
import json
import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from stages.stage_05_ci_cd.pipeline import CATEGORICAL_FEATURES, FEATURES, build_pipeline, load_dataset

LOGGER = logging.getLogger(__name__)


def train(data_path: Path, output_dir: Path) -> dict[str, float]:
    features, target = load_dataset(data_path)
    train_features, test_features, train_target, test_target = train_test_split(
        features, target, test_size=0.2, stratify=target, random_state=42,
    )
    model = build_pipeline().fit(train_features, train_target)
    prediction = model.predict(test_features)
    probability = model.predict_proba(test_features)[:, 1]
    metrics = {
        "accuracy": float(accuracy_score(test_target, prediction)),
        "precision": float(precision_score(test_target, prediction, zero_division=0)),
        "recall": float(recall_score(test_target, prediction, zero_division=0)),
        "roc_auc": float(roc_auc_score(test_target, probability)),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "heart_disease_pipeline.joblib"
    joblib.dump(model, model_path)
    reloaded = joblib.load(model_path)
    if not np.allclose(model.predict_proba(test_features), reloaded.predict_proba(test_features)):
        raise RuntimeError("Exported model failed the reload check")
    metadata = {
        "model_name": "logistic_regression_ci_baseline",
        "features": FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "target_mapping": {"0": "no disease", "1": "disease present (original num 1-4)"},
        "random_state": 42,
        "training_rows": len(train_features),
        "test_rows": len(test_features),
        "package_versions": {
            package: version(package) for package in ["joblib", "numpy", "pandas", "scikit-learn"]
        },
        "warning": "Educational model only; not for diagnosis or clinical decision-making.",
    }
    (output_dir / "model_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8",
    )
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    LOGGER.info("Training complete: %s", json.dumps(metrics))
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and smoke-test the stage-5 CI baseline")
    parser.add_argument("--data", type=Path, default=Path("data/processed/heart_disease.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/stage_05/training"))
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    train(arguments.data, arguments.output_dir)


if __name__ == "__main__":
    main()