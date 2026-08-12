#!/bin/bash
# Lit la RC-N1 et envoie les sticks au conteneur ROS2 (UDP 7777).
# Au premier usage (pas de calibration), calibre la RC avant de piloter.
cd "$(dirname "$0")/../dji"

PY="$(command -v python3 || command -v python)"
if [ -z "$PY" ]; then
    echo "Python introuvable (installez python3)."
    exit 1
fi

if [ ! -f rc_calib.json ]; then
    echo "Première utilisation : calibration de la RC..."
    exec "$PY" dji_host.py --calibrate "$@"
else
    exec "$PY" dji_host.py "$@"
fi
