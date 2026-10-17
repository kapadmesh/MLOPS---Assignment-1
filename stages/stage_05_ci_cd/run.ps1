param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
& "$PSScriptRoot/run_checks.ps1" -Python $Python