# start_server.ps1 - Starts the QUIC server, auto-clearing port 4433 if occupied

$PORT = 4433

# Find all PIDs using port $PORT
$foundPids = @()
$netstatLines = netstat -ano | Select-String ":$PORT "
foreach ($line in $netstatLines) {
    $parts = ($line.ToString().Trim() -split "\s+") | Where-Object { $_ -ne "" }
    $procId = $parts[-1]
    if ($procId -match "^\d+$" -and $procId -ne "0") {
        $foundPids += $procId
    }
}
$foundPids = $foundPids | Sort-Object -Unique

if ($foundPids.Count -gt 0) {
    Write-Host "Port $PORT in use by PID(s): $($foundPids -join ', '). Killing..." -ForegroundColor Yellow
    foreach ($procId in $foundPids) {
        taskkill /F /PID $procId 2>&1 | Out-Null
    }
    Write-Host "Waiting for socket to be released..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    Write-Host "Port $PORT cleared." -ForegroundColor Green
} else {
    Write-Host "Port $PORT is free." -ForegroundColor Green
}

# Start the server with UTF-8 output
$env:PYTHONUTF8 = '1'
Write-Host "Starting QUIC server..." -ForegroundColor Cyan
.venv\Scripts\python.exe server.py
