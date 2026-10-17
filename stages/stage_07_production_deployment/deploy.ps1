param(
    [Parameter(Mandatory = $true)]
    [string]$Context
)

$ErrorActionPreference = 'Stop'
$ManifestDirectory = $PSScriptRoot
& kubectl --context $Context apply -k $ManifestDirectory
if ($LASTEXITCODE -ne 0) { throw 'Kubernetes apply failed.' }
& kubectl --context $Context -n heart-disease rollout status deployment/heart-disease-api --timeout=180s
if ($LASTEXITCODE -ne 0) { throw 'Deployment did not become ready. Check pod events and logs.' }
& kubectl --context $Context -n heart-disease get deployments,pods,services -o wide
if ($LASTEXITCODE -ne 0) { throw 'Could not retrieve deployment state.' }