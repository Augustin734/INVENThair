from typing import TypeVar

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel

from app.erreurs import ErreurMetier

T = TypeVar("T", bound=SQLModel)


def obtenir_ou_404(session: Session, modele: type[T], id_: int, libelle: str) -> T:
    objet = session.get(modele, id_)
    if objet is None:
        raise ErreurMetier(404, "INTROUVABLE", f"{libelle} introuvable.", {"id": id_})
    return objet


def valider(session: Session) -> None:
    """Commit ; un conflit d'unicité détecté par SQLite devient une erreur 409 lisible."""
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ErreurMetier(409, "NOM_DEJA_UTILISE", "Ce nom est déjà utilisé.") from exc


def nom_deja_pris(nom: str) -> ErreurMetier:
    return ErreurMetier(409, "NOM_DEJA_UTILISE", f"« {nom} » existe déjà !", {"nom": nom})
