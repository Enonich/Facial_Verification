# Identity Verification System - Complete Startup

Write-Host "🛡️  Identity Verification System" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""

# Start Backend in new window
Write-Host "1️⃣  Starting Backend Server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; python app.py"

# Wait a bit for backend to initialize
Start-Sleep -Seconds 3

# Start Frontend in new window
Write-Host "2️⃣  Starting Frontend Server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Write-Host ""
Write-Host "✅ Both servers are starting..." -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Yellow
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to exit this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
