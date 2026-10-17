param(
    [Parameter(Mandatory = $true)]
    [string]$Context,
    [string]$BaseUrl = 'http://localhost:8080'
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$OutputDirectory = Join-Path $ProjectRoot 'artifacts/stage_07/evidence'
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
& kubectl --context $Context -n heart-disease rollout status deployment/heart-disease-api --timeout=180s
if ($LASTEXITCODE -ne 0) { throw 'Deployment is not ready.' }
& kubectl --context $Context -n heart-disease get deployments,pods,services -o wide 2>&1 | Tee-Object (Join-Path $OutputDirectory 'deployment_state.txt')
if ($LASTEXITCODE -ne 0) { throw 'Could not collect deployment state.' }
& "$ProjectRoot/stages/stage_06_model_containerization/verify_endpoint.ps1" -BaseUrl $BaseUrl -OutputDirectory $OutputDirectory
& kubectl --context $Context -n heart-disease logs -l app=heart-disease-api --all-containers=true --prefix --tail=200 2>&1 | Tee-Object (Join-Path $OutputDirectory 'api_requests.log')
if ($LASTEXITCODE -ne 0) { throw 'Could not collect API logs.' }