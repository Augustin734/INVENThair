#!/usr/bin/env bash
# Copie datée de la base dans backups/ (fonctionne même si l'appli est ouverte).
set -euo pipefail
source "$(dirname "$(readlink -f "$0")")/scripts/commun.sh"

if [ ! -x "$PY" ]; then
  echo "INVENThair n'est pas encore installé : lance ./install.sh." >&2
  exit 1
fi
cd "$RACINE"
exec "$PY" -m app.services.sauvegarde
