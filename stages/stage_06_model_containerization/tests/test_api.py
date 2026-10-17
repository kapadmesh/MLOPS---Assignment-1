import json
from pathlib import Path

import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from stages.stage_05_ci_cd.pipeline import FEATURES, build_pipeline
from stages.stage_06_model_containerization.app import create_app

STAGE_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def payload():
    return json.loads((STAGE_DIR / "sample_request.json").read_text())


@pytest.fixture
def model_paths(tmp_path, payload):
    data = pd.DataFrame([payload] * 20)
    data["age"] = list(range(40, 60))
    model = build_pipeline().fit(data[FEATURES], [0, 1] * 10)
    model_path = tmp_path / "model.joblib"
    metadata_path = tmp_path / "metadata.json"
    joblib.dump(model, model_path)
    metadata_path.write_text(json.dumps({
        "features": FEATURES, "model_name": "test", "warning": "Educational only",
    }))
    return model_path, metadata_path


@pytest.fixture
def client(model_paths):
    with TestClient(create_app(*model_paths)) as test_client:
        yield test_client


def test_prediction_and_health(client, payload):
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["prediction"] in (0, 1)
    assert result["confidence"] == result["class_probabilities"][str(result["prediction"])]
    assert sum(result["class_probabilities"].values()) == pytest.approx(1)
    assert response.headers["X-Request-ID"]


@pytest.mark.parametrize("field,value", [
    ("age", -1), ("age", "63"), ("age", None), ("sex", True),
    ("cp", 99), ("thal", 0), ("oldpeak", -1), ("extra", 1),
])
def test_invalid_request(client, payload, field, value):
    payload[field] = value
    assert client.post("/predict", json=payload).status_code == 422


def test_missing_feature(client, payload):
    del payload["age"]
    assert client.post("/predict", json=payload).status_code == 422


def test_metrics_and_private_logs(client, payload, caplog):
    with caplog.at_level("INFO", logger="uvicorn.error"):
        client.post("/predict", json=payload)
        client.post("/predict", json={})
    response = client.get("/metrics")
    assert response.status_code == 200
    assert 'api_requests_total{method="POST",route="/predict",status="200"}' in response.text
    assert 'api_requests_total{method="POST",route="/predict",status="422"}' in response.text
    assert "model_predictions_total" in response.text
    events = [json.loads(record.message) for record in caplog.records if record.message.startswith("{")]
    assert any(event.get("event") == "api_request" for event in events)
    assert all("age" not in event and "payload" not in event for event in events)


def test_startup_rejects_missing_model(tmp_path):
    with pytest.raises(FileNotFoundError), TestClient(create_app(tmp_path / "missing", tmp_path / "metadata")):
        pass


def test_startup_rejects_metadata_mismatch(model_paths):
    model_path, metadata_path = model_paths
    metadata_path.write_text(json.dumps({"features": []}))
    with pytest.raises(ValueError, match="feature contract"), TestClient(create_app(model_path, metadata_path)):
        pass


def test_not_ready_without_lifespan(model_paths, payload):
    with TestClient(create_app(*model_paths)) as test_client:
        test_client.app.state.service = None
        assert test_client.get("/ready").status_code == 503
        assert test_client.post("/predict", json=payload).status_code == 503