param(
    [ValidateSet('Up', 'Down', 'Logs')]
    [string]$Action = 'Up'
)
$ErrorActionPreference = 'Stop'
$ComposeFile = Join-Path $PSScriptRoot 'compose.yaml'
switch ($Action) {
    'Up' { & docker compose -f $ComposeFile up -d --build }
    'Down' { & docker compose -f $ComposeFile down }
    'Logs' { & docker compose -f $ComposeFile logs --tail=100 api }
}
if ($LASTEXITCODE -ne 0) { throw "Stage 06 action $Action failed." }