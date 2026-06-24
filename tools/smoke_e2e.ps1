param(
  [string]$FrontendBase = "http://localhost:4173",
  [string]$BackendBase = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

function Assert-Ok {
  param([string]$Url)
  $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -Method Get
  if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
    throw "$Url returned $($response.StatusCode)"
  }
  Write-Output "OK $Url"
}

function Assert-LegacyGone {
  param([string]$Url)
  try {
    Invoke-WebRequest -UseBasicParsing -Uri $Url -Method Post -ContentType "application/json" -Body "{}" | Out-Null
    throw "$Url did not return 410"
  } catch {
    $status = $_.Exception.Response.StatusCode.value__
    if ($status -ne 410) {
      throw "$Url returned $status instead of 410"
    }
    Write-Output "OK legacy route retired: $Url"
  }
}

Assert-Ok "$FrontendBase/index.html"
Assert-Ok "$FrontendBase/about.html"
Assert-Ok "$FrontendBase/faq.html"
Assert-Ok "$FrontendBase/login.html"
Assert-Ok "$BackendBase/api/health"
Assert-Ok "$BackendBase/api/saas/health"
Assert-Ok "$BackendBase/api/version"
Assert-LegacyGone "$BackendBase/api/projects/test-project/preflight"

Write-Output "DevBareun smoke E2E passed."
