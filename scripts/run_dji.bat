@echo off
REM Lance la lecture de la RC-N1 et envoie les sticks au conteneur ROS2.
cd /d "%~dp0\..\dji"
python dji_host.py %*
