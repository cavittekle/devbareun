param(
  [string]$FrontendUrl = "http://127.0.0.1:4173",
  [string]$BackendUrl = "",
  [switch]$SkipHttp
)

$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$failures = 0
$warnings = 0

function Pass($message) {
  Write-Host "[PASS] $message" -ForegroundColor Green
}

function Warn($message) {
  $script:warnings += 1
  Write-Host "[WARN] $message" -ForegroundColor Yellow
}

function Fail($message) {
  $script:failures += 1
  Write-Host "[FAIL] $message" -ForegroundColor Red
}

function Has-File($relativePath, $message) {
  if (Test-Path (Join-Path $repo $relativePath)) { Pass $message } else { Fail "$message ($relativePath missing)" }
}

function Has-Text($relativePath, $pattern, $message) {
  $path = Join-Path $repo $relativePath
  if (-not (Test-Path $path)) {
    Fail "$message ($relativePath missing)"
    return
  }
  $text = Get-Content $path -Raw
  if ($text -match $pattern) { Pass $message } else { Fail "$message ($pattern not found)" }
}

function Http-Check($url, $message, [switch]$WarnOnly) {
  try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 12 -MaximumRedirection 5
    if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
      Pass "$message HTTP $($response.StatusCode)"
    } elseif ($WarnOnly) {
      Warn "$message HTTP $($response.StatusCode)"
    } else {
      Fail "$message HTTP $($response.StatusCode)"
    }
    return $response.Content
  } catch {
    if ($WarnOnly) { Warn "$message unavailable: $($_.Exception.Message)" } else { Fail "$message unavailable: $($_.Exception.Message)" }
    return ""
  }
}

function Parse-Json($content) {
  try {
    return $content | ConvertFrom-Json -ErrorAction Stop
  } catch {
    return $null
  }
}

Write-Host "DevBareun production readiness check" -ForegroundColor Cyan
Write-Host "Repo: $repo"

if (Test-Path (Join-Path $repo "index.html")) {
  Fail "Repository root must not contain production index.html"
} else {
  Pass "Repository root is not a frontend deploy target"
}

Has-File "frontend/vercel.json" "Vercel config exists under frontend"
Has-File "backend/railway.json" "Railway config exists under backend"
Has-File "frontend/package.json" "Frontend build package exists"
Has-File "frontend/member-dashboard-app/package.json" "React workspace package exists"
Has-File "frontend/member-dashboard-app/package-lock.json" "React workspace lockfile exists"

if (Test-Path (Join-Path $repo "frontend/workspace/index.html")) {
  Pass "Generated /workspace/ app exists locally"
} else {
  Warn "Generated /workspace/ app is missing locally; run npm run build from frontend before static preview"
}

Has-Text "frontend/vercel.json" '"source"\s*:\s*"/workspace"' "Vercel routes /workspace to the React workspace"
Has-Text "frontend/member-dashboard-app/vite.config.js" 'base:\s*"/workspace/"' "React workspace uses /workspace/ asset base"
Has-Text "backend/.env.example" 'DEVBAREUN_PAYMENT_PROVIDER=lemonsqueezy' "Backend env example uses Lemon Squeezy"
Has-Text "backend/.env.example" 'UPSTASH_REDIS_REST_URL=' "Backend env example declares Upstash Redis URL"
Has-Text "backend/.env.example" 'DEVBAREUN_ALLOW_IN_MEMORY_RATE_LIMIT=false' "Production rate limit fallback is disabled by default"
Has-Text "backend/.env.example" 'SUPABASE_SERVICE_ROLE_KEY=' "Backend env example declares service role key only for Railway"

$frontendSecretHits = @()
$secretPatterns = @(
  "SUPABASE_SERVICE_ROLE_KEY",
  "SUPABASE_JWT_SECRET",
  "LEMON_SQUEEZY_API_KEY",
  "LEMON_SQUEEZY_WEBHOOK_SECRET",
  "UPSTASH_REDIS_REST_TOKEN"
)
foreach ($pattern in $secretPatterns) {
  $frontendFiles = Get-ChildItem -Path (Join-Path $repo "frontend") -File -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch "\\node_modules\\" -and $_.FullName -notmatch "\\workspace\\" -and $_.FullName -notmatch "\\member-dashboard-app\\dist\\" }
  $matches = $frontendFiles | Select-String -Pattern $pattern -ErrorAction SilentlyContinue
  if ($matches) { $frontendSecretHits += $matches }
}
if ($frontendSecretHits.Count -eq 0) {
  Pass "Frontend source does not contain backend-only secret variable names"
} else {
  Fail "Frontend source contains backend-only secret references"
  $frontendSecretHits | Select-Object -First 10 | ForEach-Object { Write-Host "  $($_.Path):$($_.LineNumber) $($_.Line)" -ForegroundColor Red }
}

if (-not $SkipHttp) {
  if ($FrontendUrl) {
    $front = $FrontendUrl.TrimEnd("/")
    [void](Http-Check "$front/index.html" "Frontend index")
    [void](Http-Check "$front/workspace/" "React workspace route" -WarnOnly)
  }
  if ($BackendUrl) {
    $api = $BackendUrl.TrimEnd("/")
    $health = Http-Check "$api/api/health" "Backend health" -WarnOnly
    $saasHealth = Http-Check "$api/api/saas/health" "SaaS health" -WarnOnly
    Http-Check "$api/api/version" "Backend version" -WarnOnly | Out-Null
    $healthJson = Parse-Json $health
    $saasJson = Parse-Json $saasHealth
    if ($health -match "not_configured" -or $saasHealth -match "not_configured") {
      Warn "Backend health still reports not_configured; live Supabase/Storage setup is incomplete"
    }
    $readiness = $healthJson.readiness
    if (-not $readiness) { $readiness = $saasJson.readiness }
    if ($readiness) {
      if ($readiness.production_security -ne $true) { Warn "Backend production_security is not true" }
      foreach ($flag in @("dev_auth", "local_store", "mock_payment", "pilot_login", "pilot_checkout", "legacy_project_routes", "ephemeral_upload")) {
        if ($readiness.$flag -ne "disabled") { Warn "Backend $flag is $($readiness.$flag); production should disable it" }
      }
      if ($readiness.docs -ne "disabled") { Warn "Backend docs are enabled; production should set DEVBAREUN_DISABLE_DOCS=true" }
      if ($readiness.lemonsqueezy -ne "configured") { Warn "Lemon Squeezy is not fully configured on backend" }
      if ($readiness.rate_limit -ne "upstash") { Warn "Production rate limit is not using Upstash" }
      if ($readiness.supabase_private -ne "configured") { Warn "Supabase private/service configuration is missing" }
    }
  }
}

Write-Host ""
Write-Host "Failures: $failures  Warnings: $warnings"
if ($failures -gt 0) { exit 1 }
