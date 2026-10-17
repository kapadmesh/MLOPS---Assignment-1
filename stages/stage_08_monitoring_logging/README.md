# Stage 08 - Monitoring and Logging

## Start Later

Stop the stage-06 Compose stack first to free port 8000. Copy `.env.example` to `.env` inside this stage directory and set a new nonempty Grafana password locally; do not commit it.

```powershell
Copy-Item stages/stage_08_monitoring_logging/.env.example stages/stage_08_monitoring_logging/.env
```

After filling in the password:

```powershell
.\stages\stage_08_monitoring_logging\run.ps1 -Action Up
.\stages\stage_06_model_containerization\verify_endpoint.ps1
```

Open Prometheus at `http://localhost:9090` and Grafana at `http://localhost:3000`. Log into Grafana using the local `.env` credentials. The Prometheus datasource and **MLOps / Stage 08 - Heart Disease API** dashboard are provisioned automatically.

This Compose stack monitors its own local API instance, not the stage-07 Kubernetes pods. Kubernetes pods expose the same `/metrics` endpoint and carry Prometheus scrape annotations for an existing cluster monitoring setup; those annotations alone do not install a scraper.

## Demonstrate Metrics

Generate requests for several minutes so the five-minute rate panels have enough samples:

```powershell
$Payload = Get-Content stages/stage_06_model_containerization/sample_request.json -Raw
1..100 | ForEach-Object {
    Invoke-RestMethod -Method Post -Uri http://localhost:8000/predict -ContentType 'application/json' -Body $Payload | Out-Null
}
```

Allow at least two Prometheus scrapes before inspecting rate panels. The dashboard shows availability, requests by route/status, p95 prediction latency, prediction counts by class, and 5xx error percentage. A single burst will only affect a short part of the time window. No 5xx samples can appear as an empty error series rather than a measured zero.

Alerts appear in Prometheus when the API is down or 5xx error rate exceeds five percent. No Alertmanager or external alert delivery is configured. These metrics monitor service behavior, not model quality, data drift, calibration, or clinical validity.

## Request Logging

The API writes structured JSON request events to stdout/stderr with a generated request ID, HTTP method, normalized route, status, and duration. Responses include `X-Request-ID` for correlation. Raw URLs, request bodies, patient feature values, and predictions are not included in request logs. Unmatched paths share a bounded label to avoid unbounded metric cardinality. Validation failures are measured; metrics scrapes are excluded from request metrics.

```powershell
.\stages\stage_08_monitoring_logging\run.ps1 -Action Logs
```

The same request events can be retrieved from Kubernetes with `kubectl logs`. Grafana displays metrics only; centralized log storage is not included.

## Evidence and Cleanup

Capture a healthy Prometheus target, the populated Grafana dashboard, and request-log entries after generating traffic. Store screenshots/logs under `artifacts/stage_08/evidence/` and avoid sensitive data.

```powershell
.\stages\stage_08_monitoring_logging\run.ps1 -Action Down
```

Named volumes preserve metrics and Grafana state. Adding `--volumes` deletes them. A changed Grafana admin password in `.env` does not reset credentials in an already-initialized persistent Grafana database. All demo ports bind to localhost.