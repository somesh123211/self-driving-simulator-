# Udacity Self-Driving Car Voice Assistant Dashboard PowerShell Launcher
[CmdletBinding()]
param()

$Host.UI.RawUI.WindowTitle = "Udacity Voice Assistant Dashboard"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "       UDACITY VOICE-ASSISTED AUTONOMOUS DRIVING DASHBOARD           " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

Set-Location -Path "$PSScriptRoot\.."

if (-not (Test-Path -Path "voice_command\best_model.pth")) {
    if (Test-Path -Path "best_model.pth") {
        Copy-Item -Path "best_model.pth" -Destination "voice_command\best_model.pth"
    }
}

Write-Host "`n[INFO] Launching Web Dashboard & Telemetry Server on http://localhost:4567..." -ForegroundColor Green

Start-Process "http://localhost:4567"

.\venv\Scripts\python.exe voice_command\drive_voice.py voice_command\best_model.pth
