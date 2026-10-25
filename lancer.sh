#!/usr/bin/env bash
# Lancé par le raccourci du Bureau : démarre le serveur si besoin puis ouvre la fenêtre.
set -uo pipefail
source "$(dirname "$(readlink -f "$0")")/scripts/commun.sh"

prevenir() {
  echo "$1" >&2
  command -v notify-send >/dev/null 2>&1 && notify-send -i "$RACINE/app/static/icone.svg" "INVENThair" "$1"
}

ouvrir_fenetre() {
  local navigateur
  for navigateur in chromium chromium-browser google-chrome google-chrome-stable; do
    if command -v "$navigateur" >/dev/null 2>&1; then
      setsid "$navigateur" --app="$URL" >/dev/null 2>&1 &
      return 0
    fi
  done
  setsid xdg-open "$URL" >/dev/null 2>&1 &
}

if [ ! -x "$PY" ]; then
  prevenir "INVENThair n'est pas encore installé : lance ./install.sh."
  exit 1
fi

if ! serveur_repond; then
  mkdir -p "$LOGS"
  cd "$RACINE"
  setsid nohup "$VENV/bin/uvicorn" app.main:app --host "$HOTE" --port "$PORT" \
    >>"$LOGS/inventhair.log" 2>&1 </dev/null &
  echo $! >"$FICHIER_PID"
  for _ in $(seq 1 20); do
    serveur_repond && break
    sleep 0.5
  done
  if ! serveur_repond; then
    prevenir "INVENThair n'a pas réussi à démarrer. Le détail est dans logs/inventhair.log."
    exit 1
  fi
fi

ouvrir_fenetre
