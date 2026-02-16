$ErrorActionPreference = "Continue"

# UTF-8 safety
chcp 65001 | Out-Null
$env:PYTHONUTF8="1"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$root   = $PSScriptRoot
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# IMPORTANT: do NOT touch worker.log (it may be locked by another process)
$superLog = Join-Path $logDir "supervisor.log"
$mainLog  = Join-Path $logDir "worker_out.log"

while ($true) {
    $today    = Get-Date -Format "yyyyMMdd"
    $dailyLog = Join-Path $logDir "worker_$today.log"

    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$ts] supervisor: running worker_imap.py" | Out-File -FilePath $superLog -Append -Encoding utf8

    try {
        # Run once, capture stdout+stderr, append to logs
        $out = & (Join-Path $root "venv\Scripts\python.exe") (Join-Path $root "worker_imap.py") 2>&1
        $out | Out-File -FilePath $mainLog  -Append -Encoding utf8
        $out | Out-File -FilePath $dailyLog -Append -Encoding utf8
    }
    catch {
        $err = $_.Exception.ToString()
        "[$ts] supervisor: ERROR $err" | Out-File -FilePath $superLog -Append -Encoding utf8
    }

    Start-Sleep -Seconds 60

}
