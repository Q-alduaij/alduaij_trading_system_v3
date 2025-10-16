# web\gen_token.ps1
param([string]$EnvPath = "..\.env")
$ErrorActionPreference = "Stop"

# Resolve relative to the script's folder, not the caller's CWD
$envFilePath = Join-Path -Path $PSScriptRoot -ChildPath $EnvPath
if (-not (Test-Path $envFilePath)) {
  throw ".env not found at $envFilePath"
}

$lines = Get-Content $envFilePath
$existing = $lines | Where-Object { $_ -match '^\s*DASHBOARD_TOKEN\s*=' }
if ($existing) {
  Write-Host "DASHBOARD_TOKEN already present in .env; leaving it unchanged." -ForegroundColor Yellow
  exit 0
}

$raw = [Convert]::ToBase64String((1..48 | % {Get-Random -Max 256} | % {[byte]$_}))
$token = ($raw.TrimEnd('=')) -replace '\+','-' -replace '/','_'

if (-not ($lines | Where-Object { $_ -match '^\s*DASHBOARD_PORT\s*=' })) {
  $lines += "DASHBOARD_PORT=8080"
}
$lines += "DASHBOARD_TOKEN=$token"
Set-Content -Path $envFilePath -Value $lines -Encoding UTF8

Write-Host "Wrote DASHBOARD_TOKEN to $envFilePath" -ForegroundColor Green
Write-Host "Token: $token" -ForegroundColor Cyan
