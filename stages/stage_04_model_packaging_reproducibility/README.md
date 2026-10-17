# Stage 04 - Model Packaging and Reproducibility

Resolves `models:/heart-disease-classifier@champion`, verifies its version, source run, status tags, and model-name alias against the stage-03 handoff, then loads that immutable version. After inference, export, and reload checks pass, it assigns `final-champion` to the packaged version and adds `packaging_status=final-champion` to its run and version. The previous final champion's packaging tags are archived when promotion changes.

The metadata records `model_alias=champion`, `final_model_alias=final-champion`, the model-name alias, and the exact registered version. Further stages serve this exported joblib file, so moving registry aliases does not silently change an already built container. Repackage and rebuild to update it. Registry clients can resolve the approved version with `models:/heart-disease-classifier@final-champion`.

```powershell
.\stages\stage_04_model_packaging_reproducibility\run.ps1 -Python .\.venv\Scripts\python.exe
```

Run stages 01 and 03 first. Outputs are `models/heart_disease_pipeline.joblib`, `models/model_metadata.json`, and the root `requirements.txt`.