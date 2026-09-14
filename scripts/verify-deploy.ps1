#Requires -Version 5.1
param(
  [string]$ApiBase = $env:API_BASE,
  [string]$FrontendUrl = $env:FRONTEND_URL
)
$ErrorActionPreference = "Stop"
if (-not $ApiBase) { $ApiBase = "http://localhost:8000" }
$ApiBase = $ApiBase.TrimEnd("/")

function Check($name, [scriptblock]$fn) {
  try { & $fn; Write-Output "PASS: $name" }
  catch { Write-Output "FAIL: $name -- $($_.Exception.Message)"; $script:failed = $true }
}

Check "health" {
  $h = Invoke-RestMethod "$ApiBase/api/health" -TimeoutSec 60
  if ($h.status -ne "ok") { throw "status=$($h.status)" }
  Write-Output "  jobs=$($h.jobs) storage=$($h.storage | ConvertTo-Json -Compress)"
}
Check "tools list" {
  $t = Invoke-RestMethod "$ApiBase/api/tools" -TimeoutSec 30
  if (-not $t.tools -or $t.tools.Count -lt 20) { throw "unexpected tool count" }
}
Check "maintenance stats" {
  $s = Invoke-RestMethod "$ApiBase/api/maintenance/stats" -TimeoutSec 30
  if ($null -eq $s.storage) { throw "no storage stats" }
}
Check "upload+compress roundtrip" {
  $tmp = Join-Path ([IO.Path]::GetTempPath()) "verify.pdf"
  # Build a minimal 1-page PDF (needs python + pypdf on the machine running this script)
  python -c "from pypdf import PdfWriter; w=PdfWriter(); w.add_blank_page(612,792); f=open(r'$tmp','wb'); w.write(f); f.close()"
  # PS 5.1 Invoke-RestMethod has no -Form, so upload via curl.exe (ships with Windows).
  $upJson = & curl.exe -s --fail -F "file=@$tmp;type=application/pdf" "$ApiBase/api/files/upload"
  $up = $upJson | ConvertFrom-Json
  if (-not $up.file_id) { throw "no file_id" }
  $job = Invoke-RestMethod "$ApiBase/api/tools/compress" -Method Post -ContentType "application/json" -Body (@{ file_id = $up.file_id } | ConvertTo-Json) -TimeoutSec 60
  $st = $null
  for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 2
    $st = Invoke-RestMethod "$ApiBase/api/jobs/$($job.job_id)" -TimeoutSec 30
    if ($st.status -eq "completed" -or $st.status -eq "failed") { break }
  }
  if ($st.status -ne "completed") { throw "job status=$($st.status) err=$($st.error)" }
  Remove-Item $tmp -ErrorAction SilentlyContinue
}
if ($FrontendUrl) {
  Check "frontend reachable" {
    $r = Invoke-WebRequest $FrontendUrl -UseBasicParsing -TimeoutSec 30
    if ($r.StatusCode -ge 400) { throw "HTTP $($r.StatusCode)" }
  }
}
if ($script:failed) { exit 1 }
Write-Output "All checks passed."
