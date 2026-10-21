# Independent hidden processes survive closing the invoking terminal/chat command.
$ErrorActionPreference = 'Stop'
$logDirectory = Join-Path $PSScriptRoot 'work\dev-logs'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
foreach ($server in @(@{Name='backend';Port=8000}, @{Name='frontend';Port=5173})) {
    $probe = New-Object System.Net.Sockets.TcpClient
    try { $probe.Connect('127.0.0.1', $server.Port); $occupied = $true }
    catch { $occupied = $false }
    finally { $probe.Dispose() }
    if ($occupied) {
        Write-Host "$($server.Name): port $($server.Port) already in use; existing process kept."
        continue
    }
    $arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $PSScriptRoot 'dev.ps1') + '" ' + $server.Name
    $started = Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory "$($server.Name).out.log") -RedirectStandardError (Join-Path $logDirectory "$($server.Name).err.log") -PassThru
    $started.Id | Set-Content -LiteralPath (Join-Path $logDirectory "$($server.Name).pid")
    Write-Host "$($server.Name): started PID $($started.Id). Logs: $logDirectory"
}
Write-Host 'Web: http://127.0.0.1:5173/ | Swagger: http://127.0.0.1:8000/docs'
