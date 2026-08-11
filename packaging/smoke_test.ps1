param(
    [string]$ReleaseDirectory = "dist\CoproAuto",
    [int]$TimeoutSeconds = 30,
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
