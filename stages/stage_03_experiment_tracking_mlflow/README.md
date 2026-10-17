# Stage 03 - Experiment Tracking with MLflow

Loads both models' tuned parameters from stage 02, then tracks their preprocessing pipelines, cross-validation and hold-out metrics, evaluation plots, and model artifacts. Both candidates become versions of the registered model `heart-disease-classifier`. The run with the highest mean cross-validation ROC AUC receives alias `champion`; other current versions receive `challenger-<model-name>`. Every current version also receives `model-<model-name>`, and readable `model_name`/`model_status` tags are applied to both runs and model versions.

| Alias | Meaning |
| --- | --- |
| `champion` | Highest mean CV ROC AUC in the latest stage-03 comparison |
| `challenger` | Highest-ranked non-champion in that comparison |
| `challenger-logistic-regression` / `challenger-random-forest` | Named aliases for current non-champions only |
| `model-logistic-regression` / `model-random-forest` | Latest compared version of each named model |
| `final-champion` | Champion version that most recently passed stage-04 packaging checks |

Aliases are model-registry pointers, not run tags. `model_name`, `model_status`, and selection tags describe runs and model versions. Stage 04 adds the separate `packaging_status` tag. Stage 03 leaves `final-champion` unchanged until stage 04 packages the new champion; a previous packaged version can therefore remain `final-champion` while a newer version is `champion`.

```powershell
.\stages\stage_03_experiment_tracking_mlflow\run.ps1 -Python .\.venv\Scripts\python.exe
```

Run stages 01 and 02 first. Tracking metadata and the model registry are stored in `mlflow.db`, MLflow artifacts in `mlruns/`, the complete comparison in `artifacts/stage_03/mlflow_run_summary.csv`, and the downstream alias/version handoff in `artifacts/stage_03/champion_run.json`. Champion selection never uses hold-out metrics.