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

REM Sous Windows / Docker Desktop, le rendu 3D reste en CPU (pas d'acceleration
REM GPU OpenGL possible pour Gazebo) : on n'utilise QUE le compose de base.
REM REBUILD=1 force la reconstruction locale au lieu de telecharger l'image.
if "%REBUILD%"=="1" (
    echo [2/3] REBUILD=1 : construction locale de l'image ^(plusieurs minutes^)...
    docker compose up -d --build
) else (
    docker image inspect ghcr.io/rogshutter/drone_sim:latest >nul 2>nul
    if errorlevel 1 (
        echo [2/3] Telechargement de l'image ^(ghcr.io^)...
        docker compose pull sim
    ) else (
        if "%PULL%"=="1" (
            echo [2/3] PULL=1 : mise a jour de l'image...
            docker compose pull sim
        ) else (
            echo [2/3] Image deja presente, pas de telechargement ^(PULL=1 pour mettre a jour^).
        )
    )
    docker compose up -d
)
if errorlevel 1 (
    echo.
    echo [31mECHEC du build. Regarde l'erreur ci-dessus puis relance.
    echo [0m
    exit /b 1
)

echo.
echo [3/3] Simulation lancee !
echo.
echo   - Vue 3D         : fenetre Gazebo si un ecran est dispo
echo   - QGroundControl : TCP  127.0.0.1  port 5760
echo   - Radio RC-N1    : veille automatique ci-dessous
echo.
echo Arret du simulateur : scripts\stop.bat
echo.

REM --- Veille radio (USB sur le PC, pas dans Docker) ---
where python >nul 2>nul
if errorlevel 1 (
    echo Python introuvable : sim allumee, pas de veille radio.
    echo   Installez Python 3 puis relancez, ou : python dji\dji_host.py
    endlocal
    exit /b 0
)
python -c "import serial" >nul 2>nul
if errorlevel 1 (
    echo pyserial manquant � installation...
    python -m pip install -q -r dji\requirements.txt
    if errorlevel 1 (
        echo Echec pip. Faites : python -m pip install -r dji\requirements.txt
        echo Le simulateur tourne deja.
        endlocal
        exit /b 0
    )
)
python dji\watch_rc.py
endlocal
