@echo off
REM Ouvre la VUE 3D GAZEBO (gzclient) : tu verras le drone osciller / vibrer en direct.
REM Nécessite VcXsrv (X server gratuit pour Windows) : https://sourceforge.net/projects/vcxsrv/
REM
REM Usage :
REM   1. scripts\start.bat           (la simulation tourne)
REM   2. scripts\start_gui.bat       (ouvre la fenêtre 3D)
REM   3. règles le PID dans QGC et REGARDE le drone osciller en 3D.
setlocal
cd /d "%~dp0\.."

echo Vérification de VcXsrv...
tasklist /FI "IMAGENAME eq vcxsrv.exe" 2>nul | find /I "vcxsrv.exe" >nul
if errorlevel 1 (
    if exist "C:\Program Files\VcXsrv\vcxsrv.exe" (
        echo Démarrage de VcXsrv...
        start "" "C:\Program Files\VcXsrv\vcxsrv.exe" -multiwindow -clipboard -ac
        timeout /t 3 /nobreak >nul
    ) else (
        echo.
        echo VcXsrv n'est pas installé. Téléchargez-le ici :
        echo   https://sourceforge.net/projects/vcxsrv/
        echo Lancez-le (XLaunch : "Multiple windows", "-ac" si demandé),
        echo puis relancez ce script.
        exit /b 1
    )
)

echo Lancement de la vue 3D Gazebo (gzclient)...
echo   - Modele : le drone iris dans le monde simule
echo   - Regle un PID trop faible en D dans QGC et observe l'oscillation en 3D.
REM Rendu CPU (software) sous Windows : hérité du conteneur (LIBGL_ALWAYS_SOFTWARE=1).
docker compose exec -e DISPLAY=127.0.0.1:0 sim gzclient

endlocal
