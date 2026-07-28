# start_server.ps1 - Starts the QUIC server, auto-clearing port 4433 if occupied

$PORT = 4433

# Kill ALL python processes holding port $PORT
$pids = @()
$netstatLines = netstat -ano | Select-String ":$PORT "
foreach ($line in $netstatLines) {
    $parts = ($line -split "\s+") | Where-Object { $_ -ne "" }
    $pid = $parts[-1]
    if ($pid -match "^\d+$" -and $pid -ne "0") {
        $pids += $pid
    }
}
$pids = $pids | Sort-Object -Unique

if ($pids.Count -gt 0) {
    Write-Host "Port $PORT in use by PID(s): $($pids -join ', '). Killing..." -ForegroundColor Yellow
    foreach ($p in $pids) {
        taskkill /F /PID $p 2>$null | Out-Null
    }
    Write-Host "Waiting for socket release..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2   # Give Windows time to release the UDP socket
    Write-Host "Port $PORT cleared." -ForegroundColor Green
} else {
    Write-Host "Port $PORT is free." -ForegroundColor Green
}

# Start the server with UTF-8 output
$env:PYTHONUTF8 = '1'
Write-Host "Starting QUIC server..." -ForegroundColor Cyan
.venv\Scripts\python.exe server.py
