import joblib
import numpy as np
import pandas as pd
import pytest

from stages.stage_05_ci_cd.pipeline import FEATURES, build_pipeline, load_dataset, prepare_features


def test_feature_order_and_extra_columns():
    data = pd.DataFrame([{name: 1 for name in reversed(FEATURES)}])
    data["target"] = 0
    assert prepare_features(data).columns.tolist() == FEATURES


@pytest.mark.parametrize("kind", ["missing", "empty", "text", "infinity"])
def test_invalid_features(kind):
    data = pd.DataFrame([{name: 1.0 for name in FEATURES}])
    if kind == "missing":
        data = data.drop(columns="age")
    elif kind == "empty":
        data = data.iloc[:0]
    elif kind == "text":
        data["age"] = "invalid"
    else:
        data["age"] = np.inf
    with pytest.raises(ValueError):
        prepare_features(data)


@pytest.mark.parametrize("targets", [[0, 2], [0, None], [0, 0], [0.5, 1]])
def test_invalid_target(tmp_path, targets):
    data = pd.DataFrame([{name: 1 for name in FEATURES}] * 2)
    data["target"] = targets
    path = tmp_path / "data.csv"
    data.to_csv(path, index=False)
    with pytest.raises(ValueError):
        load_dataset(path)


def test_pipeline_probabilities_missing_values_and_reload(tmp_path):
    data = pd.DataFrame([
        {name: float(index % 4 + 1) for name in FEATURES}
        for index in range(20)
    ])
    data.loc[0, "age"] = np.nan
    data.loc[1, "sex"] = np.nan
    model = build_pipeline().fit(prepare_features(data), [0, 1] * 10)
    sample = data.iloc[[0]].copy()
    sample["cp"] = 99
    probabilities = model.predict_proba(sample)
    assert probabilities.shape == (1, 2)
    assert np.all((probabilities >= 0) & (probabilities <= 1))
    assert np.allclose(probabilities.sum(axis=1), 1)
    path = tmp_path / "pipeline.joblib"
    joblib.dump(model, path)
    assert np.allclose(joblib.load(path).predict_proba(sample), probabilities)