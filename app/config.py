"""Réglages de l'appli, lus dans l'environnement et le fichier `.env`."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

RACINE = Path(__file__).resolve().parent.parent
HOTE = "127.0.0.1"
PORT = 8000

load_dotenv(RACINE / ".env")


@dataclass(frozen=True)
class Reglages:
    chemin_base: Path
    mail_destinataire_defaut: str


def lire_reglages() -> Reglages:
    chemin = os.getenv("INVENTHAIR_DB") or str(RACINE / "inventhair.db")
    return Reglages(
        chemin_base=Path(chemin).expanduser(),
        mail_destinataire_defaut=os.getenv("MAIL_DESTINATAIRE_DEFAUT", ""),
    )
