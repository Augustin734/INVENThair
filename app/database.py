"""Connexion SQLite, création des tables et données de départ.

Pas d'outil de migration en V1 : `create_all` crée les tables manquantes,
puis les catégories de départ sont insérées si la table est vide.
Lancer `python -m app.database` initialise la base sans démarrer le serveur.
"""

from collections.abc import Iterator
from pathlib import Path

from fastapi import Request
from sqlalchemy import Engine, event
from sqlmodel import Session, SQLModel, create_engine, select

from app import models  # noqa: F401  (enregistre les tables dans SQLModel.metadata)
from app.models import Categorie

CATEGORIES_DE_DEPART = [
    ("Gels", (176, 16, 80)),
    ("Vernis", (45, 81, 40)),
    ("Capsules", (121, 54, 92)),
    ("Consommables", (67, 13, 43)),
]


def creer_moteur(chemin_base: Path) -> Engine:
    chemin_base.parent.mkdir(parents=True, exist_ok=True)
    moteur = create_engine(
        f"sqlite:///{chemin_base}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(moteur, "connect")
    def _activer_cles_etrangeres(connexion, _):
        curseur = connexion.cursor()
        curseur.execute("PRAGMA foreign_keys = ON")
        curseur.close()

    return moteur


def initialiser_base(moteur: Engine) -> None:
    SQLModel.metadata.create_all(moteur)
    with Session(moteur) as session:
        if session.exec(select(Categorie)).first() is None:
            for ordre, (nom, (r, g, b)) in enumerate(CATEGORIES_DE_DEPART, start=1):
                session.add(Categorie(nom=nom, couleur_r=r, couleur_g=g, couleur_b=b, couleur_a=1.0, ordre=ordre))
            session.commit()


def obtenir_session(request: Request) -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête."""
    with Session(request.app.state.moteur) as session:
        yield session


if __name__ == "__main__":
    from app.config import lire_reglages

    reglages = lire_reglages()
    initialiser_base(creer_moteur(reglages.chemin_base))
    print(f"Base prête : {reglages.chemin_base}")
