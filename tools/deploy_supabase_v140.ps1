param(
  [string]$DbUrl = $env:SUPABASE_DB_URL,
  [switch]$SkipSeed
)

$ErrorActionPreference = "Stop"

if (-not $DbUrl) {
  throw "Set SUPABASE_DB_URL to the Supabase pooled or direct Postgres connection string before running this script."
}

if (-not (Get-Command supabase.cmd -ErrorAction SilentlyContinue)) {
  throw "supabase.cmd was not found. Install it with: npm install -g supabase"
}

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$sqlFiles = @(
  "database\2026_05_29_v140_production_saas_core.sql",
  "database\2026_05_29_v140_part2_jobs_billing_reports.sql"
)

if (-not $SkipSeed) {
  $sqlFiles += "database\seed_plans.sql"
}

foreach ($relative in $sqlFiles) {
  $path = Join-Path $root $relative
  if (-not (Test-Path -LiteralPath $path)) {
    throw "Missing SQL file: $relative"
  }
  Write-Host "Applying $relative"
  supabase.cmd db query --db-url $DbUrl --file $path
}

Write-Host "Supabase database setup completed."
Write-Host "Verify storage bucket 'project-files' exists and is private."
