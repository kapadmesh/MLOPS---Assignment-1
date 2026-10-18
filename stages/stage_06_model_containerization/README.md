# Stage 06 - Model Containerization

## API Contract

`POST /predict` accepts one flat JSON object containing all 13 features in `sample_request.json`. Category values use UCI Cleveland codes: sex/fbs/exang `0-1`, cp `1-4`, restecg `0-2`, slope `1-3`, ca `0-3`, and thal `3`, `6`, or `7`. Unknown fields, missing fields, strings, booleans, non-finite values, and invalid categories return HTTP 422. Numeric physiological fields must satisfy the bounds in the request schema. Responses contain `prediction`, `confidence` for that predicted class, `class_probabilities`, `model_name`, and an educational warning.

`GET /health` is liveness; `GET /ready` is model readiness; `GET /metrics` exposes Prometheus metrics; `/docs` exposes OpenAPI. A missing or incompatible artifact fails application startup rather than serving a substitute model. Each process loads the model once. One worker per container keeps the in-process metrics correct; use separate Kubernetes pods for replicas.

## Local Python Run Later

Install dependencies from `requirements.txt` into Python 3.13, then:

```powershell
python -m uvicorn stages.stage_06_model_containerization.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

In another terminal:

```powershell
.\stages\stage_06_model_containerization\verify_endpoint.ps1
```

On Rocky Linux, use the Bash verifier:

```bash
bash stages/stage_06_model_containerization/verify_endpoint.sh
```

## Docker Run Later

Install/start Docker Desktop in Linux-container mode. Use the repository root as the build context:

```powershell
.\stages\stage_06_model_containerization\run.ps1 -Action Up
.\stages\stage_06_model_containerization\verify_endpoint.ps1
.\stages\stage_06_model_containerization\run.ps1 -Action Logs
```

The image runs as a non-root user and includes only serving dependencies, reusable source, and the selected model/metadata. Compose binds the API to localhost, drops capabilities, and uses a read-only filesystem with writable `/tmp`.

Verification stores the prediction response and metrics in `artifacts/stage_06/verification/`. Swagger is available at `http://localhost:8000/docs` after startup.

```powershell
.\stages\stage_06_model_containerization\run.ps1 -Action Down
```

On Rocky Linux, use the Bash equivalents:

```bash
bash stages/stage_06_model_containerization/run.sh Up
bash stages/stage_06_model_containerization/verify_endpoint.sh
bash stages/stage_06_model_containerization/run.sh Logs
bash stages/stage_06_model_containerization/run.sh Down
```

Stop this stack before starting stage 08, which runs its own API on port 8000. Model and metadata are baked into the image; rebuild when either changes. `MODEL_PATH` and `MODEL_METADATA_PATH` can select alternate mounted trusted artifacts when running the Python service.

## Evidence

Capture a successful Docker build, healthy running container, and sample `/predict` response. The checked Python prediction alone is not evidence that Docker builds and runs.