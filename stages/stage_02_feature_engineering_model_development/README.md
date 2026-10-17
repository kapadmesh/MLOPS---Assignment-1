# Stage 02 - Feature Engineering and Model Development

Builds leakage-safe preprocessing, compares Logistic Regression and Random Forest with stratified cross-validation, tunes both models, and evaluates each tuned model on the same untouched hold-out set.

```powershell
.\stages\stage_02_feature_engineering_model_development\run.ps1 -Python .\.venv\Scripts\python.exe
```

Run stage 01 first. `artifacts/stage_02/tuned_model_results.csv` compares both models. Each model has its own folder containing `metrics.json`, `model.joblib`, and `holdout_evaluation.png`. `selection.json` records the stage-2 leader by cross-validation ROC AUC. Stage 03 independently tracks both candidates in MLflow and assigns the production-selection status.