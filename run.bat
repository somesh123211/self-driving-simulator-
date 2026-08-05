@echo off
title Udacity Self-Driving Car Track 1 Reverse Launcher
color 0A

echo ======================================================================
echo           UDACITY SELF-DRIVING CAR TRACK 1 REVERSE LAUNCHER            
echo ======================================================================

set MODEL_PATH=""

if exist "best_model.keras" (
    set MODEL_PATH="best_model.keras"
) else if exist "track 2part 2.keras" (
    set MODEL_PATH="track 2part 2.keras"
) else if exist "MAIN\track 2part 2.keras" (
    set MODEL_PATH="MAIN\track 2part 2.keras"
)

if %MODEL_PATH%=="" (
    color 0C
    echo.
    echo [ERROR] No trained model file ('best_model.keras') found!
    echo Please run 'py -3.10 train.py' to train the model first.
    echo.
    pause
    exit /b 1
)

echo.
echo [INFO] Detected Model: %MODEL_PATH%
echo [STEP 1/2] Checking dependencies...
py -3.10 -m pip install -r requirements.txt

echo.
echo [STEP 2/2] Launching drive.py telemetry server on port 4567...
echo [INFO] Open Udacity Simulator, select Track 1, and click Autonomous Mode.
echo.

py -3.10 drive.py %MODEL_PATH%

echo.
pause
