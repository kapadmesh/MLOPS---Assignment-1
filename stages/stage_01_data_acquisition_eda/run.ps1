param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Push-Location $ProjectRoot
try { & $Python -m stages.stage_01_data_acquisition_eda.run; if ($LASTEXITCODE -ne 0) { throw 'Stage 01 failed.' } }
finally { Pop-Location }