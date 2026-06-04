param(
  [string]$RailwayToken = $(if ($env:RAILWAY_TOKEN) { $env:RAILWAY_TOKEN } else { $env:RAILWAY_API_TOKEN }),
  [string]$ProjectId = $env:RAILWAY_PROJECT_ID,
  [string]$Service = $env:RAILWAY_SERVICE,
  [string]$Environment = $(if ($env:RAILWAY_ENVIRONMENT) { $env:RAILWAY_ENVIRONMENT } else { "production" }),
  [string]$Message = "DevBareun v1.4.0 backend deploy"
)

$ErrorActionPreference = "Stop"

if (-not $RailwayToken) {
  throw "Set RAILWAY_TOKEN or RAILWAY_API_TOKEN before running this script. Browserless login is not available in non-interactive terminals."
}

if (-not (Get-Command railway.cmd -ErrorAction SilentlyContinue)) {
  throw "railway.cmd was not found. Install it with: npm install -g @railway/cli"
}

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$backend = Join-Path $root "backend"

if (-not (Test-Path -LiteralPath (Join-Path $backend "railway.json"))) {
  throw "backend\railway.json was not found."
}

$env:RAILWAY_TOKEN = $RailwayToken
$env:RAILWAY_API_TOKEN = $RailwayToken
Push-Location $backend
try {
  $args = @("up", "--detach", "--message", $Message)
  if ($ProjectId) {
    $args += @("--project", $ProjectId)
  }
  if ($Service) {
    $args += @("--service", $Service)
  }
  if ($Environment) {
    $args += @("--environment", $Environment)
  }
  railway.cmd @args
} finally {
  Pop-Location
}

Write-Host "Railway deploy command submitted."
Write-Host "After Railway reports a healthy deployment, verify: https://YOUR-RAILWAY-DOMAIN/api/health"
