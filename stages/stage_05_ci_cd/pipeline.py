from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

FEATURES = [
    "age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
    "thalach", "exang", "oldpeak", "slope", "ca", "thal",
]
NUMERIC_FEATURES = ["age", "trestbps", "chol", "thalach", "oldpeak"]
CATEGORICAL_FEATURES = ["sex", "cp", "fbs", "restecg", "exang", "slope", "ca", "thal"]


def prepare_features(data: pd.DataFrame) -> pd.DataFrame:
    missing = set(FEATURES) - set(data.columns)
    if missing:
        raise ValueError(f"Missing features: {sorted(missing)}")
    if data.empty:
        raise ValueError("At least one row is required")
    features = data.loc[:, FEATURES].apply(pd.to_numeric, errors="raise")
    if np.isinf(features.to_numpy(dtype=float)).any():
        raise ValueError("Features cannot contain infinite values")
    return features


def load_dataset(path: Path) -> tuple[pd.DataFrame, pd.Series]:
    data = pd.read_csv(path)
    features = prepare_features(data)
    if "target" not in data or not data["target"].isin([0, 1]).all():
        raise ValueError("Dataset must contain a non-null binary target")
    target = data["target"].astype(int)
    if target.nunique() != 2:
        raise ValueError("Training requires both target classes")
    return features, target


def build_pipeline() -> Pipeline:
    preprocessing = ColumnTransformer([
        ("numeric", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]), NUMERIC_FEATURES),
        ("categorical", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), CATEGORICAL_FEATURES),
    ])
    return Pipeline([
        ("preprocessing", preprocessing),
        ("classifier", LogisticRegression(
            C=1.0, max_iter=2000, class_weight="balanced", random_state=42,
        )),
    ])