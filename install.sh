#!/usr/bin/env bash
# Installation sur le PC de Maud : environnement, base, raccourcis Bureau et menu.
# À relancer après une mise à jour du code.
set -euo pipefail
source "$(dirname "$(readlink -f "$0")")/scripts/commun.sh"

preparer_venv requirements.txt
mkdir -p "$LOGS" "$RACINE/backups"
initialiser_base
chmod +x "$RACINE"/start.sh "$RACINE"/lancer.sh "$RACINE"/stop.sh "$RACINE"/desinstaller.sh "$RACINE"/backup.sh

raccourci="$(mktemp)"
trap 'rm -f "$raccourci"' EXIT
sed "s|@RACINE@|$RACINE|g" "$RACINE/scripts/inventhair.desktop.in" >"$raccourci"

applications="$(dossier_applications)"
mkdir -p "$applications"
install -m 755 "$raccourci" "$applications/inventhair.desktop"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q "$applications" || true
echo "Raccourci ajouté au menu des applications."

bureau="$(dossier_bureau)"
if [ -d "$bureau" ]; then
  install -m 755 "$raccourci" "$bureau/inventhair.desktop"
  # GNOME demande que le lanceur soit marqué « fiable » pour l'ouvrir d'un double-clic.
  command -v gio >/dev/null 2>&1 && gio set "$bureau/inventhair.desktop" metadata::trusted true 2>/dev/null || true
  echo "Raccourci ajouté sur le Bureau ($bureau)."
else
  echo "Pas de dossier Bureau trouvé : raccourci seulement dans le menu."
fi

echo "C'est prêt ! Double-clique sur INVENThair pour lancer l'appli."
