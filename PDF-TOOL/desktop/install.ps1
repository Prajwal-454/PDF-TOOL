#Requires -Version 5.1
<#
  Installs PDF-TOOL as a normal Windows app (per-user, no admin needed):
    - copies the app to %LOCALAPPDATA%\PDF-TOOL
    - creates a private Python environment with the PDF engine
    - adds the command  PDF-TOOL  to your PATH   (type PDF-TOOL in Win+R / cmd / PowerShell)
    - adds Start-menu + Desktop shortcuts          (type PDF-TOOL in the Start menu)
  Re-run any time to update. Add -Rebuild to rebuild the web UI from source (needs Node.js).
#>
param(
  [switch]$NoDesktopShortcut,
  [switch]$Rebuild
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Root     = Join-Path $env:LOCALAPPDATA "PDF-TOOL"
$AppDir   = Join-Path $Root "app"
$Venv     = Join-Path $Root "venv"
$BinDir   = Join-Path $Root "bin"
$DataDir  = Join-Path $Root "data"

function Step($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Fail($m) { Write-Host "`nERROR: $m" -ForegroundColor Red; exit 1 }
function Check($what) { if ($LASTEXITCODE -ne 0) { Fail "$what failed (exit code $LASTEXITCODE)." } }

# ---------------------------------------------------------------- Python 3.10-3.13
function Find-Python {
  $cands = @()
  if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($v in "3.12","3.13","3.11","3.10") { $cands += @{ Exe = "py"; Args = @("-$v") } }
  }
  foreach ($n in "python","python3") {
    if (Get-Command $n -ErrorAction SilentlyContinue) { $cands += @{ Exe = $n; Args = @() } }
  }
  foreach ($v in "312","313","311","310") {
    $p = Join-Path $env:LOCALAPPDATA "Programs\Python\Python$v\python.exe"
    if (Test-Path $p) { $cands += @{ Exe = $p; Args = @() } }
  }
  foreach ($c in $cands) {
    try {
      $pyArgs = $c.Args
      $out = & $c.Exe @pyArgs -c "import sys; print(sys.executable if (3,10) <= sys.version_info[:2] <= (3,13) else '')" 2>$null
      if ($LASTEXITCODE -eq 0 -and $out -and (Test-Path ([string]$out).Trim())) { return ([string]$out).Trim() }
    } catch { }
  }
  return $null
}

Step "Looking for Python 3.10 - 3.13"
$Python = Find-Python
if (-not $Python) {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "Python not found - installing Python 3.12 with winget (per-user)..."
    winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
    $Python = Find-Python
  }
}
if (-not $Python) {
  Fail "Python 3.10-3.13 is required. Install it from https://www.python.org/downloads/ (tick 'Add python.exe to PATH'), then run this installer again."
}
Write-Host "Using $Python"

# ---------------------------------------------------------------- Web UI (static build)
$Out = Join-Path $RepoRoot "frontend\out"
if ($Rebuild -or -not (Test-Path (Join-Path $Out "index.html"))) {
  Step "Building the web UI (needs Node.js)"
  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Fail "Node.js is needed to build the UI. Install it from https://nodejs.org (LTS) and run this installer again."
  }
  Push-Location (Join-Path $RepoRoot "frontend")
  try {
    npm ci --no-audit --no-fund; Check "npm ci"
    npm run build:desktop;       Check "npm run build:desktop"
  } finally { Pop-Location }
}
if (-not (Test-Path (Join-Path $Out "index.html"))) { Fail "frontend\out\index.html not found." }

# ---------------------------------------------------------------- Stop a running copy
Step "Installing to $Root"
Get-Process -ErrorAction SilentlyContinue | Where-Object {
  $_.Path -and $_.Path.StartsWith($Root, [StringComparison]::OrdinalIgnoreCase)
} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

New-Item -ItemType Directory -Force $Root, $AppDir, $BinDir, $DataDir | Out-Null

# ---------------------------------------------------------------- Copy app files
foreach ($sub in "backend","web") {
  $p = Join-Path $AppDir $sub
  if (Test-Path $p) { Remove-Item $p -Recurse -Force }
}
robocopy (Join-Path $RepoRoot "backend") (Join-Path $AppDir "backend") /E /XD __pycache__ .pytest_cache storage tests .venv venv /XF *.pyc .env /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { Fail "Copying the backend failed." }
robocopy $Out (Join-Path $AppDir "web") /E /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { Fail "Copying the web UI failed." }
$global:LASTEXITCODE = 0
Copy-Item (Join-Path $PSScriptRoot "launcher.py") $AppDir -Force
Copy-Item (Join-Path $PSScriptRoot "PDF-TOOL.ico") $Root -Force

# ---------------------------------------------------------------- Python environment
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
  Step "Creating the Python environment"
  & $Python -m venv $Venv; Check "venv creation"
}
$VPy = Join-Path $Venv "Scripts\python.exe"
Step "Installing the PDF engine (first time takes a few minutes)"
& $VPy -m pip install --upgrade pip --quiet --disable-pip-version-check; Check "pip upgrade"
$Req = Join-Path $Root "requirements-runtime.txt"
Get-Content (Join-Path $AppDir "backend\requirements.txt") | Where-Object { $_ -notmatch '^\s*pytest' } | Set-Content $Req
& $VPy -m pip install -r $Req --disable-pip-version-check; Check "pip install"

# ---------------------------------------------------------------- Settings file (optional AI key)
$EnvFile = Join-Path $DataDir ".env"
if (-not (Test-Path $EnvFile)) {
  @"
# Optional settings for PDF-TOOL (restart the app after editing).
# Free AI summaries/Q&A: get a key at https://console.groq.com and paste it below.
GROQ_API_KEY=
"@ | Set-Content $EnvFile -Encoding UTF8
}

# ---------------------------------------------------------------- 'PDF-TOOL' command
Step "Creating the PDF-TOOL command"
@"
@echo off
start "" "%~dp0..\venv\Scripts\pythonw.exe" "%~dp0..\app\launcher.py" %*
"@ | Set-Content (Join-Path $BinDir "PDF-TOOL.cmd") -Encoding ASCII

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$parts = @(); if ($userPath) { $parts = $userPath.Split(";") | Where-Object { $_ } }
if (-not ($parts | Where-Object { $_.TrimEnd("\") -ieq $BinDir })) {
  [Environment]::SetEnvironmentVariable("Path", (($parts + $BinDir) -join ";"), "User")
}
if (-not ($env:Path.Split(";") | Where-Object { $_.TrimEnd("\") -ieq $BinDir })) { $env:Path += ";$BinDir" }

# tell Explorer / Win+R about the new PATH without needing a sign-out
try {
  Add-Type -Namespace Win32 -Name Native -ErrorAction SilentlyContinue -MemberDefinition '[DllImport("user32.dll", SetLastError=true, CharSet=CharSet.Auto)] public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam, uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);'
  $r = [UIntPtr]::Zero
  [Win32.Native]::SendMessageTimeout([IntPtr]0xffff, 0x1A, [UIntPtr]::Zero, "Environment", 2, 5000, [ref]$r) | Out-Null
} catch { }

# ---------------------------------------------------------------- Shortcuts
Step "Creating shortcuts"
function New-Shortcut($path) {
  $sh = New-Object -ComObject WScript.Shell
  $s = $sh.CreateShortcut($path)
  $s.TargetPath       = Join-Path $Venv "Scripts\pythonw.exe"
  $s.Arguments        = '"' + (Join-Path $AppDir "launcher.py") + '"'
  $s.WorkingDirectory = $Root
  $s.IconLocation     = (Join-Path $Root "PDF-TOOL.ico")
  $s.Description      = "PDF-TOOL - merge, split, compress, convert, OCR and more"
  $s.Save()
}
New-Shortcut (Join-Path ([Environment]::GetFolderPath("Programs")) "PDF-TOOL.lnk")
if (-not $NoDesktopShortcut) { New-Shortcut (Join-Path ([Environment]::GetFolderPath("Desktop")) "PDF-TOOL.lnk") }

# ---------------------------------------------------------------- Self-test
Step "Self-test"
& $VPy (Join-Path $AppDir "launcher.py") --check
Check "self-test"

Write-Host "`nPDF-TOOL is installed." -ForegroundColor Green
Write-Host "Open it by typing  PDF-TOOL  in the Start menu, in Win+R, or in a (new) terminal window."
Write-Host "Your files and settings live in: $DataDir"
