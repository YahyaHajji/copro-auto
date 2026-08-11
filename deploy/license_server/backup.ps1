param(
    [Parameter(Mandatory = $true)][string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$deploy = $PSScriptRoot
$resolvedOutput = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $resolvedOutput | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$destination = Join-Path $resolvedOutput "copro-license-$stamp.sql"
Push-Location $deploy
try {
    docker compose exec -T database pg_dump -U $env:POSTGRES_USER -d $env:POSTGRES_DB --clean --if-exists | Set-Content -LiteralPath $destination -Encoding utf8
}
finally {
    Pop-Location
}
Write-Output $destination
