param(
  [string]$OutputDir = "dist",
  [string]$Name = "devbareun-release"
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
if ([System.IO.Path]::IsPathRooted($OutputDir)) {
  $outRoot = $OutputDir
} else {
  $outRoot = Join-Path $root $OutputDir
}
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$stage = Join-Path $outRoot "$Name-$stamp"
$zip = "$stage.zip"

$includeDirs = @("frontend", "backend", "database", "docs", "tools", ".github")
$includeFiles = @("README.md", "AGENTS.md", ".env.example", ".gitignore")
$excludeDirNames = @(".git", ".codex", ".agents", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", "dist")
$excludeFileNames = @(".env", ".env.local", ".env.production", ".DS_Store")

New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
if (Test-Path $stage) {
  Remove-Item -LiteralPath $stage -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $stage | Out-Null

function Copy-ReleaseItem {
  param([string]$RelativePath)
  $source = Join-Path $root $RelativePath
  if (!(Test-Path $source)) { return }
  $target = Join-Path $stage $RelativePath
  if ((Get-Item $source).PSIsContainer) {
    Get-ChildItem -LiteralPath $source -Recurse -Force | ForEach-Object {
      $item = $_
      $relative = $item.FullName.Substring($source.Length).TrimStart("\", "/")
      $parts = $relative -split "[\\/]"
      if ($parts | Where-Object { $excludeDirNames -contains $_ }) { return }
      if (!$item.PSIsContainer -and ($excludeFileNames -contains $item.Name -or $item.Name.EndsWith(".log"))) { return }
      $dest = Join-Path $target $relative
      if ($item.PSIsContainer) {
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
      } else {
        New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
        Copy-Item -LiteralPath $item.FullName -Destination $dest -Force
      }
    }
  } else {
    New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
    Copy-Item -LiteralPath $source -Destination $target -Force
  }
}

foreach ($dir in $includeDirs) { Copy-ReleaseItem $dir }
foreach ($file in $includeFiles) { Copy-ReleaseItem $file }

Get-ChildItem -LiteralPath $stage -Force | Compress-Archive -DestinationPath $zip -Force
Write-Output "Created $zip"
