# LLM Council - Start script for Windows
# Run with: powershell -ExecutionPolicy Bypass -File start.ps1

Write-Host "Starting LLM Council..." -ForegroundColor Green
Write-Host ""

# Store current directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Start backend in a new window
Write-Host "Starting backend on http://localhost:8001..." -ForegroundColor Cyan
$backendProcess = Start-Process -FilePath "uv" -ArgumentList "run", "python", "-m", "backend.main" -PassThru

# Wait a bit for backend to start
Start-Sleep -Seconds 2

# Start frontend in a new window
Write-Host "Starting frontend on http://localhost:5173..." -ForegroundColor Cyan
Push-Location frontend
$frontendProcess = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -PassThru
Pop-Location

Write-Host ""
Write-Host "✓ LLM Council is running!" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8001" -ForegroundColor Yellow
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Yellow
Write-Host ""
Write-Host "Both servers are running in separate windows." -ForegroundColor Gray
Write-Host "Close this window or press Ctrl+C to stop both servers" -ForegroundColor Gray

# Handle cleanup on Ctrl+C
try {
    # Wait for processes to exit or user interruption
    while (-not $backendProcess.HasExited -and -not $frontendProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
}
catch {
    # User pressed Ctrl+C or error occurred
    Write-Host "`nStopping servers..." -ForegroundColor Yellow
}
finally {
    # Clean up processes
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($frontendProcess -and -not $frontendProcess.HasExited) {
        Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Servers stopped." -ForegroundColor Green
}
