#Requires -Version 5.1
param([switch]$KeepData)
$ErrorActionPreference = "Stop"
$Root   = Join-Path $env:LOCALAPPDATA "PDF-TOOL"
$BinDir = Join-Path $Root "bin"

Get-Process -ErrorAction SilentlyContinue | Where-Object {
  $_.Path -and $_.Path.StartsWith($Root, [StringComparison]::OrdinalIgnoreCase)
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

foreach ($lnk in (Join-Path ([Environment]::GetFolderPath("Programs")) "PDF-TOOL.lnk"),
                 (Join-Path ([Environment]::GetFolderPath("Desktop")) "PDF-TOOL.lnk")) {
  if (Test-Path $lnk) { Remove-Item $lnk -Force }
}

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath) {
  $kept = $userPath.Split(";") | Where-Object { $_ -and ($_.TrimEnd("\") -ine $BinDir) }
  [Environment]::SetEnvironmentVariable("Path", ($kept -join ";"), "User")
}

if (Test-Path $Root) {
  if ($KeepData) {
    Get-ChildItem $Root -Force | Where-Object { $_.Name -ne "data" } | Remove-Item -Recurse -Force
  } else {
    Remove-Item $Root -Recurse -Force
  }
}
Write-Host "PDF-TOOL has been removed." -ForegroundColor Green
