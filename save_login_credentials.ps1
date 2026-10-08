$ErrorActionPreference = "Stop"

$runtimeDir = Join-Path $PSScriptRoot "runtime"
$usernamePath = Join-Path $runtimeDir "seller_sprite_username.txt"
$passwordPath = Join-Path $runtimeDir "seller_sprite_password.dpapi"

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

$username = Read-Host "SellerSprite account"
if ([string]::IsNullOrWhiteSpace($username)) {
    Write-Error "SellerSprite account cannot be empty."
    exit 2
}

$password = Read-Host "SellerSprite password" -AsSecureString
Set-Content -LiteralPath $usernamePath -Value $username.Trim() -Encoding UTF8
$password | ConvertFrom-SecureString | Set-Content -LiteralPath $passwordPath -Encoding ASCII

Write-Host "Login information encrypted successfully."
