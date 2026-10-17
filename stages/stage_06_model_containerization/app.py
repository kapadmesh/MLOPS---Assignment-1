import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest

from stages.stage_06_model_containerization.schemas import PredictionRequest, PredictionResponse
from stages.stage_06_model_containerization.service import ModelService

LOGGER = logging.getLogger("uvicorn.error")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def create_app(model_path: Path | None = None, metadata_path: Path | None = None) -> FastAPI:
    model_path = model_path or Path(os.getenv(
        "MODEL_PATH", str(PROJECT_ROOT / "models/heart_disease_pipeline.joblib"),
    ))
    metadata_path = metadata_path or Path(os.getenv(
        "MODEL_METADATA_PATH", str(PROJECT_ROOT / "models/model_metadata.json"),
    ))
    registry = CollectorRegistry()
    requests = Counter(
        "api_requests_total", "Completed API requests", ["method", "route", "status"],
        registry=registry,
    )
    latency = Histogram(
        "api_request_duration_seconds", "API request latency", ["method", "route"],
        registry=registry,
    )
    predictions = Counter(
        "model_predictions_total", "Successful model predictions", ["prediction"],
        registry=registry,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.service = ModelService(model_path, metadata_path)
        LOGGER.info(json.dumps({"event": "model_loaded", "model_name": application.state.service.metadata["model_name"]}))
        yield
        application.state.service = None

    application = FastAPI(
        title="Heart Disease Educational API", version="1.0.0", lifespan=lifespan,
        description="Educational model scores only. Not for diagnosis or clinical decisions.",
    )
    application.state.service = None

    @application.middleware("http")
    async def log_and_measure(request: Request, call_next):
        request_id = str(uuid4())
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration = time.perf_counter() - started
            route = getattr(request.scope.get("route"), "path", "unmatched")
            method = request.method if request.method in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"} else "OTHER"
            if route != "/metrics":
                requests.labels(method, route, str(status)).inc()
                latency.labels(method, route).observe(duration)
            LOGGER.info(json.dumps({
                "event": "api_request", "request_id": request_id, "method": method,
                "route": route, "status": status, "duration_seconds": round(duration, 6),
            }))

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "alive"}

    @application.get("/ready")
    def ready() -> dict[str, str]:
        if application.state.service is None:
            raise HTTPException(status_code=503, detail="Model is not ready")
        return {"status": "ready"}

    @application.post("/predict", response_model=PredictionResponse)
    def predict(payload: PredictionRequest) -> PredictionResponse:
        service = application.state.service
        if service is None:
            raise HTTPException(status_code=503, detail="Model is not ready")
        result = service.predict(payload)
        predictions.labels(str(result.prediction)).inc()
        return result

    @application.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(registry), headers={"Content-Type": CONTENT_TYPE_LATEST})

    return application


app = create_app()