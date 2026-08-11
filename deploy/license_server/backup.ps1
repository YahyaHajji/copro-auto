param(
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [string]$EnvironmentFile = (Join-Path $PSScriptRoot '.env'),
    [string]$PgDumpExecutable = ''
)

$ErrorActionPreference = 'Stop'
$deploy = $PSScriptRoot
$resolvedEnvironment = [IO.Path]::GetFullPath($EnvironmentFile)
if (-not (Test-Path -LiteralPath $resolvedEnvironment -PathType Leaf)) {
    throw "Fichier d'environnement introuvable : $resolvedEnvironment"
}

function Import-DotEnv([string]$Path) {
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) {
            continue
        }
        if ($trimmed -notmatch '^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
            throw "Ligne .env invalide : $line"
        }
        $name = $Matches[1]
        $value = $Matches[2].Trim()
        if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $values[$name] = $value
    }
    return $values
}

function Get-DatabaseSetting([hashtable]$Values, [string]$Name, [switch]$Required) {
    $value = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ([string]::IsNullOrWhiteSpace($value) -and $Values.ContainsKey($Name)) {
        $value = $Values[$Name]
    }
    if ($Required -and [string]::IsNullOrWhiteSpace($value)) {
        throw "La variable $Name est obligatoire dans l'environnement ou $resolvedEnvironment."
    }
    return $value
}

function ConvertTo-NativeArgument([string]$Value) {
    return '"' + $Value.Replace('"', '\"') + '"'
}

$environmentValues = Import-DotEnv $resolvedEnvironment
$postgresDatabase = Get-DatabaseSetting $environmentValues 'POSTGRES_DB' -Required
$postgresUser = Get-DatabaseSetting $environmentValues 'POSTGRES_USER' -Required
$postgresPassword = Get-DatabaseSetting $environmentValues 'POSTGRES_PASSWORD' -Required
$resolvedOutput = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $resolvedOutput | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$destination = Join-Path $resolvedOutput "copro-license-$stamp.sql"
$partialDestination = "$destination.partial"
$errorFile = [IO.Path]::GetTempFileName()
$previousPassword = [Environment]::GetEnvironmentVariable('PGPASSWORD', 'Process')

if ($PgDumpExecutable) {
    $executable = [IO.Path]::GetFullPath($PgDumpExecutable)
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw "pg_dump introuvable : $executable"
    }
    $arguments = @()
    $postgresHost = Get-DatabaseSetting $environmentValues 'PGHOST'
    $postgresPort = Get-DatabaseSetting $environmentValues 'PGPORT'
    if ($postgresHost) {
        $arguments += @('-h', $postgresHost)
    }
    if ($postgresPort) {
        $arguments += @('-p', $postgresPort)
    }
    $arguments += @('-U', $postgresUser, '-d', $postgresDatabase)
}
else {
    $docker = Get-Command docker -CommandType Application -ErrorAction Stop
    $executable = $docker.Source
    $arguments = @(
        'compose', '--env-file', $resolvedEnvironment, 'exec', '-T', 'database',
        'pg_dump', '-U', $postgresUser, '-d', $postgresDatabase
    )
}
$arguments += @('--clean', '--if-exists', '--no-owner', '--no-privileges', '--format=plain')
$argumentLine = ($arguments | ForEach-Object { ConvertTo-NativeArgument ([string]$_) }) -join ' '

Push-Location $deploy
try {
    [Environment]::SetEnvironmentVariable('PGPASSWORD', $postgresPassword, 'Process')
    $process = Start-Process -FilePath $executable -ArgumentList $argumentLine -Wait -PassThru -NoNewWindow `
        -RedirectStandardOutput $partialDestination -RedirectStandardError $errorFile
    if ($process.ExitCode -ne 0) {
        $errorMessage = (Get-Content -LiteralPath $errorFile -Raw).Trim()
        throw "La sauvegarde PostgreSQL a échoué (code $($process.ExitCode)) : $errorMessage"
    }
    if (-not (Test-Path -LiteralPath $partialDestination -PathType Leaf) -or (Get-Item -LiteralPath $partialDestination).Length -eq 0) {
        throw 'La sauvegarde PostgreSQL est vide.'
    }
    Move-Item -LiteralPath $partialDestination -Destination $destination -Force
}
catch {
    if (Test-Path -LiteralPath $partialDestination) {
        Remove-Item -LiteralPath $partialDestination -Force
    }
    throw
}
finally {
    [Environment]::SetEnvironmentVariable('PGPASSWORD', $previousPassword, 'Process')
    if (Test-Path -LiteralPath $errorFile) {
        Remove-Item -LiteralPath $errorFile -Force
    }
    Pop-Location
}
Write-Output $destination
