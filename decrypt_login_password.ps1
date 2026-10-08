param(
    [Parameter(Mandatory = $true)]
    [string]$PasswordFile
)

$ErrorActionPreference = "Stop"
$utf8 = New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $false
[Console]::OutputEncoding = $utf8

if (-not (Test-Path -LiteralPath $PasswordFile)) {
    throw "The encrypted SellerSprite password file does not exist."
}

# ConvertFrom-SecureString writes one encrypted line followed by a newline.
# Read only that line and trim it before asking Windows DPAPI to decrypt it.
$encrypted = (Get-Content -LiteralPath $PasswordFile -First 1).Trim()
if ([string]::IsNullOrWhiteSpace($encrypted)) {
    throw "The encrypted SellerSprite password file is empty."
}

$securePassword = ConvertTo-SecureString -String $encrypted
$credential = New-Object -TypeName System.Management.Automation.PSCredential -ArgumentList "SellerSprite", $securePassword
[Console]::Out.Write($credential.GetNetworkCredential().Password)
