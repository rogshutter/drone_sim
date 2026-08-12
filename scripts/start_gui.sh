#!/bin/bash
# Ouvre la vue 3D Gazebo (gzclient). Sous Linux/WSL2 avec WSLg, rien à installer.
set -e
cd "$(dirname "$0")/.."

export DISPLAY="${DISPLAY:-:0}"
echo "Lancement de la vue 3D Gazebo (gzclient) sur DISPLAY=$DISPLAY ..."
docker compose exec -e DISPLAY="$DISPLAY" -e LIBGL_ALWAYS_SOFTWARE=1 sim gzclient
