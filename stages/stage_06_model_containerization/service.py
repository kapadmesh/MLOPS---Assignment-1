import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from stages.stage_05_ci_cd.pipeline import FEATURES, prepare_features
from stages.stage_06_model_containerization.schemas import PredictionRequest, PredictionResponse


class ModelService:
    def __init__(self, model_path: Path, metadata_path: Path) -> None:
        self.model = joblib.load(model_path)
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if self.metadata.get("features") != FEATURES:
            raise ValueError("Model metadata does not match the API feature contract")
        if set(self.model.feature_names_in_) != set(FEATURES):
            raise ValueError("Model does not match the API feature contract")
        if self.model.classes_.tolist() != [0, 1]:
            raise ValueError("The API requires a binary classifier with classes 0 and 1")

    def predict(self, request: PredictionRequest) -> PredictionResponse:
        features = prepare_features(pd.DataFrame([request.model_dump()]))
        prediction = int(self.model.predict(features)[0])
        probabilities = self.model.predict_proba(features)[0]
        if not np.isfinite(probabilities).all() or not np.isclose(probabilities.sum(), 1):
            raise RuntimeError("Model returned invalid probabilities")
        return PredictionResponse(
            prediction=prediction,
            confidence=float(probabilities[prediction]),
            class_probabilities={
                str(int(label)): float(score)
                for label, score in zip(self.model.classes_, probabilities, strict=True)
            },
            model_name=self.metadata["model_name"],
            warning=self.metadata["warning"],
        )