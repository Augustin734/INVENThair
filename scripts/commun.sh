# shellcheck shell=bash
# Fonctions partagées par start.sh, install.sh, lancer.sh, stop.sh et desinstaller.sh.

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$RACINE/.venv"
PY="$VENV/bin/python"
HOTE="127.0.0.1"
PORT="8000"
URL="http://$HOTE:$PORT"
LOGS="$RACINE/logs"
FICHIER_PID="$LOGS/inventhair.pid"

trouver_python() {
  local p
  for p in python3.13 python3.12 python3.11 python3; do
    if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

# Crée le venv si besoin et (ré)installe les dépendances quand un requirements*.txt a changé.
preparer_venv() {
  local requirements="$1" python empreinte actuelle
  if [ ! -x "$PY" ]; then
    python="$(trouver_python)" || { echo "Python 3.11 ou plus récent est nécessaire." >&2; return 1; }
    echo "Création de l'environnement Python…"
    "$python" -m venv "$VENV" || return 1
  fi
  empreinte="$VENV/.empreinte-$requirements"
  actuelle="$(cat "$RACINE"/requirements*.txt | sha256sum | cut -d' ' -f1)"
  if [ ! -f "$empreinte" ] || [ "$(cat "$empreinte")" != "$actuelle" ]; then
    echo "Installation des dépendances ($requirements)…"
    "$VENV/bin/pip" install --quiet --upgrade pip &&
      "$VENV/bin/pip" install --quiet -r "$RACINE/$requirements" &&
      echo "$actuelle" >"$empreinte"
  fi
}

initialiser_base() {
  (cd "$RACINE" && "$PY" -m app.database)
}

# Vrai si INVENThair répond sur /health.
serveur_repond() {
  python3 - "$URL/api/v1/health" <<'PYEOF' >/dev/null 2>&1
import json, sys, urllib.request
with urllib.request.urlopen(sys.argv[1], timeout=1) as r:
    sys.exit(0 if json.load(r).get("status") == "ok" else 1)
PYEOF
}

# PID du serveur lancé par lancer.sh, s'il tourne encore.
pid_serveur() {
  local pid
  [ -f "$FICHIER_PID" ] || return 1
  pid="$(cat "$FICHIER_PID")"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && grep -q "uvicorn" "/proc/$pid/cmdline" 2>/dev/null; then
    echo "$pid"
    return 0
  fi
  rm -f "$FICHIER_PID"
  return 1
}

dossier_bureau() {
  local d=""
  command -v xdg-user-dir >/dev/null 2>&1 && d="$(xdg-user-dir DESKTOP 2>/dev/null)"
  [ -n "$d" ] && [ "$d" != "$HOME" ] || d="$HOME/Desktop"
  echo "$d"
}

dossier_applications() {
  echo "${XDG_DATA_HOME:-$HOME/.local/share}/applications"
}
