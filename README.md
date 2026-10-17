# Heart Disease MLOps Project

Educational only. Predictions and confidence are model scores, not calibrated clinical risk estimates or medical advice.

## Stage Structure

Every stage is self-contained under `stages/` and has the same primary entry point: `run.ps1`. Python stages use an adjacent `run.py`; stage-specific tests, manifests, container files, monitoring configuration, and helper scripts stay in the owning stage folder.

| Stage | Folder | Guide |
| --- | --- | --- |
| 01 - Acquisition and EDA | `stages/stage_01_data_acquisition_eda/` | [Stage 01](stages/stage_01_data_acquisition_eda/README.md) |
| 02 - Feature engineering and models | `stages/stage_02_feature_engineering_model_development/` | [Stage 02](stages/stage_02_feature_engineering_model_development/README.md) |
| 03 - MLflow experiment tracking | `stages/stage_03_experiment_tracking_mlflow/` | [Stage 03](stages/stage_03_experiment_tracking_mlflow/README.md) |
| 04 - Packaging and reproducibility | `stages/stage_04_model_packaging_reproducibility/` | [Stage 04](stages/stage_04_model_packaging_reproducibility/README.md) |
| 05 - CI/CD and automated testing | `stages/stage_05_ci_cd/` | [Stage 05](stages/stage_05_ci_cd/README.md) |
| 06 - Containerization and API | `stages/stage_06_model_containerization/` | [Stage 06](stages/stage_06_model_containerization/README.md) |
| 07 - Production deployment | `stages/stage_07_production_deployment/` | [Stage 07](stages/stage_07_production_deployment/README.md) |
| 08 - Monitoring and logging | `stages/stage_08_monitoring_logging/` | [Stage 08](stages/stage_08_monitoring_logging/README.md) |

Generated evidence uses matching `artifacts/stage_XX/` folders. Shared inputs remain in `data/`, the selected serving artifact remains in `models/`, and MLflow's backend remains in `mlflow.db` and `mlruns/`. The GitHub Actions workflow stays under `.github/workflows/`, where GitHub requires it.

## Run Pattern

Run stage scripts from the project root. Stages 01-05 accept the selected Python executable; stages 06-08 use their documented Docker or Kubernetes parameters.

```powershell
.\stages\stage_01_data_acquisition_eda\run.ps1 -Python .\.venv\Scripts\python.exe
.\stages\stage_02_feature_engineering_model_development\run.ps1 -Python .\.venv\Scripts\python.exe
.\stages\stage_03_experiment_tracking_mlflow\run.ps1 -Python .\.venv\Scripts\python.exe
.\stages\stage_04_model_packaging_reproducibility\run.ps1 -Python .\.venv\Scripts\python.exe
.\stages\stage_05_ci_cd\run.ps1 -Python .\.venv\Scripts\python.exe
```

Use each linked stage guide for prerequisites, stage 06-08 commands, verification, and cleanup.

## Setup Later

Commands in the stage guides are intended to be run later, from the project root in PowerShell. No packages, containers, cluster resources, or hosting are installed by adding these files.

Use Python **3.13**, matching the existing artifact environment. `requirements.txt` is the single project dependency file and includes the analysis, training, serving, lint, test, and MLflow dependencies used across the project. Direct dependencies are version-pinned; this is not a complete transitive lockfile.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Reuse the existing virtual environment instead of recreating it when appropriate. Docker Desktop and Kubernetes/kubectl are separate later prerequisites.

## Model Handoff

The serving image loads `models/heart_disease_pipeline.joblib` and `models/model_metadata.json` from stage 04. Keep both in the repository or provision them before the CI Docker build. Stage 03 registers both candidates under `heart-disease-classifier`, assigns aliases `champion`, `challenger`, `challenger-<model-name>`, and `model-<model-name>`, and writes `artifacts/stage_03/champion_run.json`. Run/version name and status tags remain readable in MLflow. Stage 04 resolves `champion`, rejects mismatched provenance, and promotes the verified packaged version to `final-champion`. CI trains a separate deterministic logistic-regression baseline under `artifacts/stage_05/training/`; it does **not** rerun MLflow model selection, overwrite the selected artifact, or automatically promote that baseline to production. Deployment is deliberately manual.

Only load joblib artifacts from trusted sources: deserialization can execute code. Model and metadata must agree on the 13-feature contract and classes `[0, 1]`. Repackage stage 04 and rebuild the image whenever changing the selected model or its compatible dependency versions.

## Verification Status

The existing environment was used to verify dataset loading, training/export/reload, input validation, registry aliases/name tags, and a prediction from the packaged model. YAML/JSON parsing and Python syntax were checked. The sample returned prediction `0` with confidence approximately `0.5665` for the current Random Forest final champion.

Full pytest/Ruff execution, Docker build/run, GitHub Actions execution, Kubernetes endpoint verification, and dashboard screenshots require the later installation and hosting steps. No deployment screenshots are fabricated. Each stage guide describes the evidence to capture.