#!/usr/bin/env bash
# Arrête le serveur lancé depuis le Bureau.
set -uo pipefail
source "$(dirname "$(readlink -f "$0")")/scripts/commun.sh"

if pid="$(pid_serveur)"; then
  kill "$pid"
  for _ in $(seq 1 20); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.25
  done
  rm -f "$FICHIER_PID"
  echo "INVENThair est arrêté."
elif serveur_repond; then
  echo "Un serveur INVENThair tourne mais n'a pas été lancé depuis le Bureau (./start.sh ? Ctrl+C dans son terminal)." >&2
  exit 1
else
  echo "INVENThair ne tournait pas."
fi
