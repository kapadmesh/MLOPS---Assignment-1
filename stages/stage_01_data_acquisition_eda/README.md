# Stage 01 - Data Acquisition and EDA

Downloads the UCI Cleveland Heart Disease dataset, converts the diagnosis to a binary target, imputes source missing values, and writes exploratory plots.

```powershell
.\.venv\Scripts\python.exe -m stages.stage_01_data_acquisition_eda.run
```

Outputs are `data/processed/heart_disease.csv` and `artifacts/stage_01/`. Internet access is required for the UCI download.