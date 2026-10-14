param([switch]$FromStdin)

$ErrorActionPreference = "Stop"
$tokenPath = Join-Path $PSScriptRoot "runtime\github_token.dpapi"
New-Item -ItemType Directory -Force -Path (Split-Path $tokenPath) | Out-Null
if ($FromStdin) {
    $reader = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), (New-Object System.Text.UTF8Encoding($false)))
    $plainToken = $reader.ReadLine()
    if ([string]::IsNullOrWhiteSpace($plainToken)) { throw "GitHub token cannot be empty." }
    $token = ConvertTo-SecureString -String $plainToken.Trim() -AsPlainText -Force
    $plainToken = $null
} else {
    $token = Read-Host "GitHub fine-grained personal access token" -AsSecureString
}
$token | ConvertFrom-SecureString | Set-Content -LiteralPath $tokenPath -Encoding ASCII
Write-Host "GitHub token encrypted for this Windows user."
