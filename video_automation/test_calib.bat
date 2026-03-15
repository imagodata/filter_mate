@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo TEST: Lancer la calibration ? [O/n]
set /p DO_CALIB="    > "
echo DO_CALIB=[!DO_CALIB!]
if /i "!DO_CALIB!"=="n" (
    echo SKIP
) else (
    python run.py --calibrate
)
echo done
