# web\start_dashboard.ps1
param([int]$Port = 8080)
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

function Get-DotEnv {
  param([string]$Path)
  $m = @{}
  if (Test-Path $Path) {
    Get-Content $Path | % {
      if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
      if ($_ -match '^\s*([^=]+)\s*=\s*(.*)\s*$') { $m[$Matches[1].Trim()] = $Matches[2].Trim() }
    }
  }
  $m
}

$envMap = Get-DotEnv ".\.env"
if (-not $envMap.ContainsKey("DASHBOARD_TOKEN")) { throw "DASHBOARD_TOKEN missing in .env" }
$token = $envMap["DASHBOARD_TOKEN"]
if ($envMap.ContainsKey("DASHBOARD_PORT")) { $Port = [int]$envMap["DASHBOARD_PORT"] }

if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) { throw "No .venv found." }
. .\.venv\Scripts\Activate.ps1

try {
  if (-not (Get-NetFirewallRule -DisplayName "Lolo Dashboard $Port" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "Lolo Dashboard $Port" -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port | Out-Null
  }
} catch {}

Start-Process powershell -ArgumentList "-NoLogo","-NoExit","-Command","cd `"$repoRoot`"; . .\.venv\Scripts\Activate.ps1; uvicorn web.dashboard:app --host 0.0.0.0 --port $Port"
Write-Host "Started Uvicorn on 0.0.0.0:$Port" -ForegroundColor Cyan

# Find cloudflared
$cf = "cloudflared"
try { & $cf --version | Out-Null } catch {
  $cfExe = (Get-ChildItem "C:\Program Files\Cloudflare" -Recurse -Filter cloudflared.exe -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
  if (-not $cfExe) { throw "cloudflared.exe not found. winget install Cloudflare.cloudflared" }
  $cf = $cfExe
}

# Run cloudflared and capture the hostname from stdout
$tmp = New-TemporaryFile
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName  = $cf
$psi.Arguments = "tunnel --url http://localhost:$Port"
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$psi.UseShellExecute = $false
$proc = [System.Diagnostics.Process]::Start($psi)

$hostname = $null
while (-not $proc.HasExited) {
  $line = $proc.StandardOutput.ReadLine()
  if ($null -ne $line) {
    $line | Out-File -Append -FilePath $tmp
    if (-not $hostname -and $line -match 'https://([a-z0-9\-]+\.trycloudflare\.com)') {
      $hostname = $Matches[1]
      $publicUrl = "https://$hostname/?token=$token"
      Write-Host ""
      Write-Host "Public URL:" -ForegroundColor Green
      Write-Host "  $publicUrl" -ForegroundColor Green
      # Open a QR for quick sharing
      Start-Process "https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=$([uri]::EscapeDataString($publicUrl))"
      # Also show simple health URL
      Write-Host "Health:" -ForegroundColor Yellow
      Write-Host "  https://$hostname/healthz" -ForegroundColor Yellow
      Write-Host ""
    }
    Write-Host $line
  } else {
    Start-Sleep -Milliseconds 120
  }
}

# After cloudflared stops, show LAN URL + QR (optional)
try {
  $ip = (Get-NetIPConfiguration | ? {$_.IPv4DefaultGateway} | % IPv4Address).IPAddress
  $lanUrl = "http://${ip}:$Port/?token=$([uri]::EscapeDataString($token))"
  Write-Host "Local URL: $lanUrl" -ForegroundColor Cyan
  Start-Process "https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=$([uri]::EscapeDataString($lanUrl))"
} catch {}
