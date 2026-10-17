param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Push-Location $ProjectRoot
try {
	$PreviousPreference = $ErrorActionPreference
	$ErrorActionPreference = 'Continue'
	& $Python -m stages.stage_03_experiment_tracking_mlflow.run
	$ExitCode = $LASTEXITCODE
	$ErrorActionPreference = $PreviousPreference
	if ($ExitCode -ne 0) { throw "Stage 03 failed with exit code $ExitCode." }
}
finally { Pop-Location }