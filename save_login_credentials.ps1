param([switch]$FromStdin)

$ErrorActionPreference = "Stop"

$runtimeDir = Join-Path $PSScriptRoot "runtime"
$usernamePath = Join-Path $runtimeDir "seller_sprite_username.txt"
$passwordPath = Join-Path $runtimeDir "seller_sprite_password.dpapi"

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

if ($FromStdin) {
    $reader = New-Object System.IO.StreamReader([Console]::OpenStandardInput(), (New-Object System.Text.UTF8Encoding($false)))
    $username = $reader.ReadLine()
    $plainPassword = $reader.ReadLine()
    if ([string]::IsNullOrWhiteSpace($plainPassword)) {
        Write-Error "SellerSprite password cannot be empty."
        exit 2
    }
    $password = ConvertTo-SecureString -String $plainPassword -AsPlainText -Force
    $plainPassword = $null
} else {
    $username = Read-Host "SellerSprite account"
    $password = Read-Host "SellerSprite password" -AsSecureString
}
if ([string]::IsNullOrWhiteSpace($username)) {
    Write-Error "SellerSprite account cannot be empty."
    exit 2
}

Set-Content -LiteralPath $usernamePath -Value $username.Trim() -Encoding UTF8
$password | ConvertFrom-SecureString | Set-Content -LiteralPath $passwordPath -Encoding ASCII

Write-Host "Login information encrypted successfully."
