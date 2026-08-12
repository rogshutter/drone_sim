#!/bin/bash
# Arrête la simulation (Linux natif / WSL2). Mêmes fichiers compose que start.sh.
cd "$(dirname "$0")/.."
COMPOSE_FILES="-f docker-compose.yml"
[ -f docker-compose.linux.yml ] && COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.linux.yml"
docker compose $COMPOSE_FILES down
echo "Simulation arrêtée."
