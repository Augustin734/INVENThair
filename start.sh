#!/usr/bin/env bash
# Lancement développeur : serveur au premier plan avec rechargement automatique.
set -euo pipefail
source "$(dirname "$(readlink -f "$0")")/scripts/commun.sh"

if serveur_repond; then
  echo "INVENThair tourne déjà sur $URL (lancé depuis le bureau ?). Arrête-le avec ./stop.sh." >&2
  exit 1
fi

preparer_venv requirements-dev.txt
initialiser_base
cd "$RACINE"
echo "INVENThair sur $URL (Ctrl+C pour arrêter)"
exec "$VENV/bin/uvicorn" app.main:app --host "$HOTE" --port "$PORT" --reload --reload-dir app
