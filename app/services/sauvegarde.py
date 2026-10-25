"""Sauvegarde de la base (US15) : copie datée dans `backups/`, à côté du fichier de base.

Utilise l'API de sauvegarde de SQLite : la copie est cohérente même si l'appli
est en train d'écrire. Lancer `python -m app.services.sauvegarde` (ou ./backup.sh)
fait une sauvegarde sans passer par le serveur.
"""

import sqlite3
from pathlib import Path

from app.models import maintenant


def dossier_sauvegardes(chemin_base: Path) -> Path:
    return chemin_base.parent / "backups"


def sauvegarder(chemin_base: Path) -> Path:
    dossier = dossier_sauvegardes(chemin_base)
    dossier.mkdir(parents=True, exist_ok=True)
    base = f"{chemin_base.stem}-{maintenant():%Y-%m-%d-%H%M%S}"
    cible, n = dossier / f"{base}.db", 2
    while cible.exists():  # deux sauvegardes dans la même seconde
        cible, n = dossier / f"{base}-{n}.db", n + 1

    source = sqlite3.connect(chemin_base)
    copie = sqlite3.connect(cible)
    try:
        with copie:
            source.backup(copie)
    finally:
        copie.close()
        source.close()
    return cible


if __name__ == "__main__":
    from app.config import lire_reglages

    chemin = lire_reglages().chemin_base
    if not chemin.exists():
        raise SystemExit(f"Pas de base à sauvegarder : {chemin}")
    print(f"Sauvegarde créée : {sauvegarder(chemin)}")
