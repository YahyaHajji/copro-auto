param(
    [string]$ReleaseDirectory = "dist\CoproAuto",
    [int]$TimeoutSeconds = 30,
    [string]$CadSamplePath = "",
    [switch]$RequireValidSignature
)

$ErrorActionPreference = "Stop"
$release = (Resolve-Path -LiteralPath $ReleaseDirectory).Path
$executable = Join-Path $release "CoproAuto.exe"
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "Exécutable introuvable : $executable"
}

$signature = Get-AuthenticodeSignature -LiteralPath $executable
if ($RequireValidSignature -and $signature.Status -ne "Valid") {
    throw "Signature Authenticode invalide ou absente : $($signature.Status)"
}

$profile = Join-Path ([System.IO.Path]::GetTempPath()) ("CoproAuto-smoke-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $profile | Out-Null
$saved = @{
    COPRO_AUTO_DEV_LICENSE = $env:COPRO_AUTO_DEV_LICENSE
    COPRO_AUTO_LICENSE_SERVER = $env:COPRO_AUTO_LICENSE_SERVER
    COPRO_AUTO_LOG_DIR = $env:COPRO_AUTO_LOG_DIR
    COPRO_AUTO_SMOKE_CAD = $env:COPRO_AUTO_SMOKE_CAD
    LOCALAPPDATA = $env:LOCALAPPDATA
    APPDATA = $env:APPDATA
}

function Invoke-CoproSmoke([string]$Name, [bool]$DevelopmentLicense) {
    if ($DevelopmentLicense) {
        $env:COPRO_AUTO_DEV_LICENSE = "1"
    } else {
        Remove-Item Env:COPRO_AUTO_DEV_LICENSE -ErrorAction SilentlyContinue
    }
    $env:COPRO_AUTO_LICENSE_SERVER = "http://127.0.0.1:9"
    $env:LOCALAPPDATA = Join-Path $profile $Name
    $env:APPDATA = Join-Path $profile $Name
    $env:COPRO_AUTO_LOG_DIR = Join-Path $profile "$Name\Logs"
    New-Item -ItemType Directory -Force -Path $env:LOCALAPPDATA | Out-Null

    $process = Start-Process -FilePath $executable -ArgumentList "--smoke-test" -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        Stop-Process -Id $process.Id -Force
        throw "Le test '$Name' a dépassé $TimeoutSeconds secondes."
    }
    if ($process.ExitCode -ne 0) {
        throw "Le test '$Name' a échoué avec le code $($process.ExitCode)."
    }
    Write-Output "PASS $Name"
}

try {
    Invoke-CoproSmoke "licensed-offline" $true
    Invoke-CoproSmoke "fresh-unlicensed" $false
    if ($CadSamplePath) {
        $cadSample = (Resolve-Path -LiteralPath $CadSamplePath).Path
        if ([System.IO.Path]::GetExtension($cadSample).ToLowerInvariant() -ne ".dxf") {
            throw "Le smoke test CAD exige un fichier DXF."
        }
        $env:COPRO_AUTO_SMOKE_CAD = $cadSample
        $env:COPRO_AUTO_LOG_DIR = Join-Path $profile "cad-dxf\Logs"
        $cadProcess = Start-Process -FilePath $executable -ArgumentList "--smoke-cad" -WindowStyle Hidden -PassThru
        if (-not $cadProcess.WaitForExit($TimeoutSeconds * 1000)) {
            Stop-Process -Id $cadProcess.Id -Force
            throw "Le test 'cad-dxf' a dépassé $TimeoutSeconds secondes."
        }
        if ($cadProcess.ExitCode -ne 0) {
            throw "Le test 'cad-dxf' a échoué avec le code $($cadProcess.ExitCode)."
        }
        Write-Output "PASS cad-dxf"
    }
    $hash = (Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash
    Write-Output "SHA256 $hash"
    Write-Output "SIGNATURE $($signature.Status)"
}
finally {
    foreach ($name in $saved.Keys) {
        $value = $saved[$name]
        if ($null -eq $value) {
            Remove-Item "Env:$name" -ErrorAction SilentlyContinue
        } else {
            Set-Item "Env:$name" $value
        }
    }
    Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue
}
