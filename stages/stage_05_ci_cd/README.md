# Stage 05 - CI/CD and Automated Testing

## Run Later

Install `requirements-dev.txt` using Python 3.13 as described in the root guide, then run:

```powershell
.\stages\stage_05_ci_cd\run.ps1 -Python .\.venv\Scripts\python.exe
```

This runs Ruff, pytest with coverage/JUnit reports, and reproducible model training. Failures stop the script. Reports and logs go to `artifacts/stage_05/reports/`; training artifacts go to `artifacts/stage_05/training/`.

For training alone:

```powershell
python -m stages.stage_05_ci_cd.train --data data/processed/heart_disease.csv --output-dir artifacts/stage_05/training
```

Tests cover feature ordering, missing/invalid inputs, binary target validation, preprocessing with missing/unseen values, model probabilities and reloads, training exports, API validation, health/readiness, metrics, privacy-conscious request logging, and failed model startup. API tests train a small temporary model rather than depending on MLflow or network access.

## GitHub Actions

Commit the project, including the cleaned dataset and stage-04 model/metadata, to a GitHub repository. The stage-05 workflow runs on pushes, pull requests, and manual dispatch. It installs the dedicated development requirements, lints, tests, trains, builds Docker, and smoke-tests `/ready`, `/predict`, and `/metrics`.

`set -o pipefail` prevents log collection from masking failed commands. Artifacts are uploaded with `if: always()` under a unique run/attempt name, retained for 14 days. They include dependency/lint/test/training/build logs, JUnit XML, coverage XML, baseline metrics/model/metadata, and container verification output when those steps were reached. Container logs are captured and the test container is removed on exit.

This workflow is a CI quality gate and packaging pipeline. It does not push images, require cloud credentials, or deploy automatically. Stage 07 is the manual deployment stage.

## Evidence

Capture the successful Actions run and its artifact list; retain JUnit/coverage results and training metrics. A workflow that has not run is not evidence of a passing pipeline.