"""Réglages de l'appli, lus dans l'environnement et le fichier `.env`."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

RACINE = Path(__file__).resolve().parent.parent
HOTE = "127.0.0.1"
PORT = 8000

load_dotenv(RACINE / ".env")

Securite = Literal["starttls", "ssl", "aucune"]


@dataclass(frozen=True)
class Reglages:
    chemin_base: Path
    mail_destinataire_defaut: str
    smtp_hote: str
    smtp_port: int
    smtp_securite: Securite
    smtp_utilisateur: str
    smtp_mot_de_passe: str
    smtp_expediteur: str

    @property
    def envoi_mail_configure(self) -> bool:
        return bool(self.smtp_hote and self.smtp_expediteur)


def _securite(port: int) -> Securite:
    valeur = os.getenv("SMTP_SECURITE", "").strip().lower()
    if valeur in ("starttls", "ssl", "aucune"):
        return valeur
    return "ssl" if port == 465 else "starttls"


def lire_reglages() -> Reglages:
    """Relu à chaque appel : une modification du .env est prise en compte au redémarrage, et les tests peuvent changer l'environnement."""
    chemin = os.getenv("INVENTHAIR_DB") or str(RACINE / "inventhair.db")
    try:
        port = int(os.getenv("SMTP_PORT") or 587)
    except ValueError:
        port = 587
    return Reglages(
        chemin_base=Path(chemin).expanduser(),
        mail_destinataire_defaut=os.getenv("MAIL_DESTINATAIRE_DEFAUT", "").strip(),
        smtp_hote=os.getenv("SMTP_HOTE", "").strip(),
        smtp_port=port,
        smtp_securite=_securite(port),
        smtp_utilisateur=os.getenv("SMTP_UTILISATEUR", "").strip(),
        smtp_mot_de_passe=os.getenv("SMTP_MOT_DE_PASSE", ""),
        smtp_expediteur=os.getenv("SMTP_EXPEDITEUR", "").strip(),
    )


def obtenir_reglages() -> Reglages:
    """Dépendance FastAPI."""
    return lire_reglages()
