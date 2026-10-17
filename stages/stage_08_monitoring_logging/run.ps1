param(
    [ValidateSet('Up', 'Down', 'Logs')]
    [string]$Action = 'Up'
)
$ErrorActionPreference = 'Stop'
$ComposeFile = Join-Path $PSScriptRoot 'compose.yaml'
$EnvironmentFile = Join-Path $PSScriptRoot '.env'
if (-not (Test-Path $EnvironmentFile)) {
    throw "Create $EnvironmentFile from .env.example and set GRAFANA_ADMIN_PASSWORD first."
}
switch ($Action) {
    'Up' { & docker compose --env-file $EnvironmentFile -f $ComposeFile up -d --build }
    'Down' { & docker compose --env-file $EnvironmentFile -f $ComposeFile down }
    'Logs' { & docker compose --env-file $EnvironmentFile -f $ComposeFile logs --tail=100 api }
}
if ($LASTEXITCODE -ne 0) { throw "Stage 08 action $Action failed." }