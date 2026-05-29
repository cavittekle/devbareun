param(
  [Parameter(Mandatory = $true)]
  [string]$BaseUrl
)

$ErrorActionPreference = "Stop"

$normalized = $BaseUrl.TrimEnd("/")
$healthUrl = "$normalized/api/health"
$saasHealthUrl = "$normalized/api/saas/health"

Write-Host "Checking $healthUrl"
$health = Invoke-RestMethod -Uri $healthUrl -Method Get
$health | ConvertTo-Json -Depth 8

Write-Host "Checking $saasHealthUrl"
$saasHealth = Invoke-RestMethod -Uri $saasHealthUrl -Method Get
$saasHealth | ConvertTo-Json -Depth 8
