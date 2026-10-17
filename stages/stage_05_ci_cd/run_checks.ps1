param(
    [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PreviousPythonPath = $env:PYTHONPATH

function Invoke-LoggedPython {
    param([string[]]$Arguments, [string]$LogPath)
    $PreviousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $Python @Arguments 2>&1 | Tee-Object -FilePath $LogPath
        $ExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PreviousPreference
    }
    if ($ExitCode -ne 0) { throw "Python command failed with exit code $ExitCode. See $LogPath" }
}

Push-Location $ProjectRoot
try {
    $env:PYTHONPATH = $ProjectRoot
    $Reports = Join-Path $ProjectRoot 'artifacts/stage_05/reports'
    New-Item -ItemType Directory -Force -Path $Reports | Out-Null
    Invoke-LoggedPython -Arguments @('-m', 'ruff', 'check', 'stages') -LogPath (Join-Path $Reports 'lint.log')
    Invoke-LoggedPython -Arguments @('-m', 'pytest', "--junitxml=$Reports/junit.xml", '--cov=stages.stage_05_ci_cd', '--cov=stages.stage_06_model_containerization', "--cov-report=xml:$Reports/coverage.xml") -LogPath (Join-Path $Reports 'tests.log')
    Invoke-LoggedPython -Arguments @('-m', 'stages.stage_05_ci_cd.train') -LogPath (Join-Path $Reports 'training.log')
}
finally {
    $env:PYTHONPATH = $PreviousPythonPath
    Pop-Location
}