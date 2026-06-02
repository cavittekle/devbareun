param(
  [string]$DbUrl = $env:SUPABASE_DB_URL,
  [switch]$SkipSeed
)

$ErrorActionPreference = "Stop"

if (-not $DbUrl) {
  throw "Set SUPABASE_DB_URL to the Supabase pooled or direct Postgres connection string before running this script."
}

if ($DbUrl -match "BURAYA|CONNECTION_STRING|your-|replace_|postgresql://$") {
  throw "SUPABASE_DB_URL still looks like a placeholder. Replace it with the real Supabase Postgres connection string."
}

if ($DbUrl -notmatch "^postgres(ql)?://") {
  throw "SUPABASE_DB_URL must start with postgres:// or postgresql://."
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
  & supabase.cmd db query --db-url $DbUrl --file $path
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to apply $relative. Fix the database connection or SQL error, then rerun the script."
  }
}

Write-Host "Supabase database setup completed."
Write-Host "Verify storage bucket 'project-files' exists and is private."
