@echo off
REM Lance la lecture de la RC-N1 et envoie les sticks au conteneur ROS2.
REM Au premier usage (pas de calibration), calibre la RC avant de piloter.
cd /d "%~dp0\..\dji"

if not exist "rc_calib.json" (
    echo Premiere utilisation : calibration de la RC...
    python dji_host.py --calibrate %*
) else (
    python dji_host.py %*
)
