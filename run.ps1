# Udacity Self-Driving Car Track 1 Reverse Launcher for PowerShell
[CmdletBinding()]
param()

$Host.UI.RawUI.WindowTitle = "Udacity Self-Driving Car Track 1 Reverse Launcher"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "          UDACITY SELF-DRIVING CAR TRACK 1 REVERSE LAUNCHER            " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$modelPath = $null

if (Test-Path -Path "best_model.keras") {
    $modelPath = "best_model.keras"
} elseif (Test-Path -Path "track 2part 2.keras") {
    $modelPath = "track 2part 2.keras"
} elseif (Test-Path -Path "MAIN\track 2part 2.keras") {
    $modelPath = "MAIN\track 2part 2.keras"
}

if (-not $modelPath) {
    Write-Host "`n[ERROR] No trained model ('best_model.keras') found!" -ForegroundColor Red
    Write-Host "Please run 'py -3.10 train.py' to train the model first." -ForegroundColor Yellow
    Read-Host -Prompt "Press Enter to exit..."
    Exit
}

Write-Host "`n[INFO] Found Model at: $modelPath" -ForegroundColor Cyan
Write-Host "[STEP 1/2] Checking dependencies..." -ForegroundColor Green
py -3.10 -m pip install -r requirements.txt

Write-Host "`n[STEP 2/2] Launching drive.py telemetry server on port 4567..." -ForegroundColor Green
Write-Host "[INFO] Open Udacity Simulator, select Track 1, and enter Autonomous Mode.`n" -ForegroundColor Yellow

py -3.10 drive.py $modelPath
