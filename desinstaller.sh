#!/usr/bin/env bash
# Retire les raccourcis. La base, les sauvegardes et le code restent en place.
set -uo pipefail
source "$(dirname "$(readlink -f "$0")")/scripts/commun.sh"

"$RACINE/stop.sh" >/dev/null 2>&1 || true
rm -f "$(dossier_applications)/inventhair.desktop" "$(dossier_bureau)/inventhair.desktop"
echo "Raccourcis retirés. Ta base et tes sauvegardes sont conservées."
