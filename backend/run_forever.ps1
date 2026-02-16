chcp 65001 | Out-Null
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

New-Item -ItemType Directory -Force -Path .\logs | Out-Null

$today = Get-Date -Format "yyyyMMdd"
$log = ".\logs\worker_$today.log"

$lastKbRefresh = Get-Date "2000-01-01"
$kbEveryHours = 6

while ($true) {
    try {
        # KB refresh every N hours
        if ((New-TimeSpan -Start $lastKbRefresh -End (Get-Date)).TotalHours -ge $kbEveryHours) {
            "[$(Get-Date -Format s)] KB refresh starting" | Tee-Object -FilePath $log -Append
            python .\kb_refresh.py 2>&1 | Tee-Object -FilePath $log -Append
            "[$(Get-Date -Format s)] KB refresh done" | Tee-Object -FilePath $log -Append
            $lastKbRefresh = Get-Date
        }

        # Worker run
        python .\worker_imap.py 2>&1 | Tee-Object -FilePath $log -Append
    }
    catch {
        "[$(Get-Date -Format s)] ERROR: $($_.Exception.Message)" | Tee-Object -FilePath $log -Append
    }

    Start-Sleep -Seconds 60
}
