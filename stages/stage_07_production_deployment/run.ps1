param(
    [Parameter(Mandatory = $true)]
    [string]$Context
)
$ErrorActionPreference = 'Stop'
& "$PSScriptRoot/deploy.ps1" -Context $Context