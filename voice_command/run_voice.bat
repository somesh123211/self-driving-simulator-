@echo off
title Udacity Self-Driving Car Voice Assistant Dashboard
color 0B

echo ======================================================================
echo       UDACITY VOICE-ASSISTED AUTONOMOUS DRIVING DASHBOARD           
echo ======================================================================

cd /d "%~dp0.."

if not exist "voice_command\best_model.pth" (
    if exist "best_model.pth" (
        copy "best_model.pth" "voice_command\best_model.pth"
    )
)

echo [INFO] Dependencies loaded.
echo [INFO] Launching Voice Web Dashboard & Telemetry Server on http://localhost:4567...
echo.

start "" "http://localhost:4567"

.\venv\Scripts\python.exe voice_command\drive_voice.py voice_command\best_model.pth

pause
