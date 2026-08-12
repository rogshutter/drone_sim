#!/bin/bash
# Démarre la simulation complète (Linux natif / WSL2).
#
# Détection du système :
#   - Linux natif / WSL2 -> Docker Engine Linux  (ce script)
#   - Windows             -> Docker Desktop      (scripts/start.bat)
#
# Ce script corrige aussi une config ~/.docker/config.json héritée d'un Docker
# Desktop ("credsStore": "desktop"), inconnue de Docker Engine Linux et qui fait
# échouer tout build avec "error getting credentials ... docker-credential-desktop".
set -e
cd "$(dirname "$0")/.."

# --- 1) Docker CLI présent ? ---
if ! command -v docker >/dev/null 2>&1; then
    echo "Docker introuvable."
    echo "  Ubuntu/Debian : sudo apt install docker.io docker-compose-v2"
    echo "  Autres distros : https://docs.docker.com/engine/install/"
    exit 1
fi

# --- 2) Démon Docker démarré ? ---
if ! docker info >/dev/null 2>&1; then
    echo "Le démon Docker ne répond pas. Tentative de démarrage..."
    sudo systemctl start docker >/dev/null 2>&1 || true
    if ! docker info >/dev/null 2>&1; then
        echo "Impossible de démarrer Docker automatiquement. Faites :"
        echo "    sudo systemctl start docker"
        echo "puis relancez ce script."
        exit 1
    fi
fi

# --- 3) Corrige une config Docker Desktop héritée, incompatible avec Docker Linux ---
if [ -f "$HOME/.docker/config.json" ] && grep -q '"desktop"' "$HOME/.docker/config.json"; then
    echo "Config Docker Desktop détectée ($HOME/.docker/config.json) :"
    echo "  le helper 'credsStore: desktop' est inconnu de Docker Engine Linux."
    cp "$HOME/.docker/config.json" "$HOME/.docker/config.json.bak-$(date +%s)"
    python3 - "$HOME/.docker/config.json" <<'PY'
import json, sys
p = sys.argv[1]
with open(p) as f:
    d = json.load(f)
d.pop('credsStore', None)
d.pop('credHelpers', None)
with open(p, 'w') as f:
    json.dump(d, f, indent=2)
PY
    echo "  Config corrigée (sauvegarde .bak conservée à côté)."
fi

# --- 4) Vue 3D : prépare l'accès X11 du conteneur (socket + authentification) ---
# L'authentification X est copiée vers un chemin stable (~/.docker-xauth), car le
# fichier Xauthority (Xwayland) change à chaque session et ne peut pas être monté
# en dur dans docker-compose.linux.yml.
export DISPLAY="${DISPLAY:-}"
export XDOCKER_XAUTH="$HOME/.docker-xauth"
if [ -n "$DISPLAY" ] && [ -n "${XAUTHORITY:-}" ] && [ -f "${XAUTHORITY:-}" ]; then
    cp -f "$XAUTHORITY" "$XDOCKER_XAUTH" && chmod 600 "$XDOCKER_XAUTH"
    echo "Vue 3D activée : DISPLAY=$DISPLAY (socket X11 monté dans le conteneur)."
else
    # Pas de serveur X accessible : on démarre sans vue 3D (rviz=off).
    # La vue 3D reste possible plus tard via scripts/start_gui.sh avec un serveur X.
    export DISPLAY=""
    export XDOCKER_XAUTH="/dev/null"
    echo "Aucun serveur X accessible : lancement sans vue 3D (headless)."
fi

# Fichiers compose : l'override Linux monte le socket X11 + l'auth X.
COMPOSE_FILES="-f docker-compose.yml"
[ -f docker-compose.linux.yml ] && COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.linux.yml"

echo "[1/3] Docker vérifié (Engine Linux)."
echo "[2/3] Construction et démarrage des conteneurs (premier lancement : plusieurs minutes)..."
docker compose $COMPOSE_FILES up -d --build

echo "[3/3] Simulation lancée !"
echo
echo "  - QGroundControl : lien UDP, port 14550"
echo "  - MAVROS / ROS2   : automatique dans le conteneur sim"
echo "  - Manette RC-N1   : python dji/dji_host.py"
echo "  - Vue 3D          : scripts/start_gui.sh"
echo
echo "Pour arrêter : scripts/stop.sh"
