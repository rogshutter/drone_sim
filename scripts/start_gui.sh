#!/bin/bash
# Ouvre la vue 3D Gazebo (gzclient). Sous Linux/WSL2 avec WSLg, rien à installer.
set -e
cd "$(dirname "$0")/.."

export DISPLAY="${DISPLAY:-:0}"
echo "Lancement de la vue 3D Gazebo (gzclient) sur DISPLAY=$DISPLAY ..."
# LIBGL_ALWAYS_SOFTWARE n'est PAS forcé ici : gzclient hérite du réglage du
# conteneur (CPU software par défaut, GPU matériel si start.sh a activé l'overlay).
docker compose exec -e DISPLAY="$DISPLAY" sim gzclient
