param(
    [string]$BaseUrl = 'http://localhost:8000',
    [string]$OutputDirectory = ''
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $ProjectRoot 'artifacts/stage_06/verification'
}
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$Payload = Get-Content (Join-Path $PSScriptRoot 'sample_request.json') -Raw
$Health = Invoke-RestMethod -Uri "$BaseUrl/health"
$Ready = Invoke-RestMethod -Uri "$BaseUrl/ready"
$Result = Invoke-RestMethod -Method Post -Uri "$BaseUrl/predict" -ContentType 'application/json' -Body $Payload
if ($Health.status -ne 'alive' -or $Ready.status -ne 'ready') { throw 'Health check failed.' }
if ($Result.prediction -notin @(0, 1)) { throw 'Prediction must be binary.' }
if ($Result.confidence -lt 0 -or $Result.confidence -gt 1) { throw 'Confidence is out of range.' }
$ProbabilitySum = $Result.class_probabilities.'0' + $Result.class_probabilities.'1'
if ([Math]::Abs($ProbabilitySum - 1) -gt 0.000001) { throw 'Probabilities do not sum to one.' }
$Result | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $OutputDirectory 'prediction_response.json')
$Metrics = Invoke-WebRequest -Uri "$BaseUrl/metrics" -UseBasicParsing
if ($Metrics.Content -notmatch 'model_predictions_total') { throw 'Prediction metrics are missing.' }
$Metrics.Content | Set-Content (Join-Path $OutputDirectory 'metrics.txt')
$Result | ConvertTo-Json -Depth 5