param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Push-Location $ProjectRoot
try { & $Python -m stages.stage_02_feature_engineering_model_development.run; if ($LASTEXITCODE -ne 0) { throw 'Stage 02 failed.' } }
finally { Pop-Location }