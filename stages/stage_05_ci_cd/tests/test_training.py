import json

import joblib
import pandas as pd

from stages.stage_05_ci_cd.pipeline import FEATURES
from stages.stage_05_ci_cd.train import train


def test_training_exports_model_metadata_and_metrics(tmp_path):
    data = pd.DataFrame([
        {name: float(index % 4 + 1) for name in FEATURES}
        for index in range(40)
    ])
    data["target"] = [0, 1] * 20
    data_path = tmp_path / "data.csv"
    data.to_csv(data_path, index=False)
    output = tmp_path / "training"
    metrics = train(data_path, output)
    assert all(0 <= score <= 1 for score in metrics.values())
    metadata = json.loads((output / "model_metadata.json").read_text())
    assert metadata["features"] == FEATURES
    assert metadata["training_rows"] + metadata["test_rows"] == 40
    assert json.loads((output / "metrics.json").read_text()) == metrics
    assert joblib.load(output / "heart_disease_pipeline.joblib").predict(data[FEATURES]).shape == (40,)