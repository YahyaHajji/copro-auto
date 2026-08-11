param(
    [Parameter(Mandatory = $true)][string]$CertificateThumbprint,
    [string]$ReleaseDirectory = "dist\CoproAuto",
    [string]$TimestampServer = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"
$release = (Resolve-Path -LiteralPath $ReleaseDirectory).Path
$executable = Join-Path $release "CoproAuto.exe"
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "Exécutable introuvable : $executable"
}

$normalized = $CertificateThumbprint.Replace(" ", "").ToUpperInvariant()
$certificate = @(
    Get-ChildItem Cert:\CurrentUser\My, Cert:\LocalMachine\My -CodeSigningCert |
        Where-Object { $_.Thumbprint.ToUpperInvariant() -eq $normalized }
) | Select-Object -First 1
if ($null -eq $certificate) {
    throw "Certificat de signature de code introuvable : $normalized"
}
if (-not $certificate.HasPrivateKey) {
    throw "Le certificat sélectionné ne possède pas de clé privée."
}
$now = Get-Date
if ($certificate.NotBefore -gt $now -or $certificate.NotAfter -lt $now) {
    throw "Le certificat n'est pas valide à la date courante."
}

$result = Set-AuthenticodeSignature -LiteralPath $executable -Certificate $certificate -HashAlgorithm SHA256 -TimestampServer $TimestampServer
if ($result.Status -ne "Valid") {
    throw "Échec de signature Authenticode : $($result.Status) — $($result.StatusMessage)"
}

$verified = Get-AuthenticodeSignature -LiteralPath $executable
if ($verified.Status -ne "Valid" -or $verified.SignerCertificate.Thumbprint -ne $certificate.Thumbprint) {
    throw "La vérification post-signature a échoué."
}

Write-Output "SIGNED $executable"
Write-Output "THUMBPRINT $($certificate.Thumbprint)"
Write-Output "SHA256 $((Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash)"
