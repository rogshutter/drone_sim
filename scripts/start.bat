@echo off
REM Démarre la simulation complète : Gazebo + ArduPilot SITL + ROS2
REM 1) Vérifie Docker Desktop, 2) build + up, 3) affiche les instructions
setlocal
cd /d "%~dp0\.."

where docker >nul 2>nul
if errorlevel 1 (
    echo Docker introuvable. Installez Docker Desktop puis relancez.
    exit /b 1
)

echo [1/3] Démarrage de Docker Desktop si nécessaire...
for /f "tokens=*" %%i in ('docker info --format {{.ServerVersion}} 2^>nul') do set DOCKER_OK=%%i
if not defined DOCKER_OK (
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Attente de Docker Desktop...
    :waitdocker
    timeout /t 3 /nobreak >nul
    docker info >nul 2>nul
    if errorlevel 1 goto waitdocker
)

echo [2/3] Construction et démarrage des conteneurs (premier lancement : plusieurs minutes)...
docker compose up -d --build
if errorlevel 1 (
    echo.
    echo [31mECHEC du build. Regarde l'erreur ci-dessus puis relance.
    echo [0m
    exit /b 1
)

echo.
echo [3/3] Simulation lancée !
echo.
echo   - QGroundControl : lien UDP, port 14550 (aperçu 3D + réglage PID)
echo   - MAVROS / ROS2   : demarre automatiquement dans le conteneur sim
echo   - Manette RC-N1   : lancer dans un autre terminal :
echo         python "%~dp0..\dji\dji_host.py"
echo.
echo Pour arreter : scripts\stop.bat
endlocal
