"""Mouvements : réception, sortie, historique (US5–US7)."""

from sqlmodel import Session, select

from app import schemas
from app.erreurs import ErreurMetier
from app.models import Mouvement, Produit, TypeMouvement
from app.services.commun import valider
from app.services.produits import obtenir
from app.services.stock import appliquer_mouvement


def _vers_schema(mouvement: Mouvement, produit: Produit) -> schemas.Mouvement:
    return schemas.Mouvement(**mouvement.model_dump(), produit_nom=produit.nom, unite=produit.unite)


def _du_plus_recent():
    # À la seconde près, l'id départage deux mouvements enregistrés en même temps.
    return Mouvement.cree_le.desc(), Mouvement.id.desc()


def historique(session: Session, produit_id: int) -> list[schemas.Mouvement]:
    produit = obtenir(session, produit_id)
    mouvements = session.exec(select(Mouvement).where(Mouvement.produit_id == produit.id).order_by(*_du_plus_recent()))
    return [_vers_schema(m, produit) for m in mouvements]


def derniers(session: Session, limite: int) -> list[schemas.Mouvement]:
    lignes = session.exec(
        select(Mouvement, Produit).join(Produit, Produit.id == Mouvement.produit_id).order_by(*_du_plus_recent()).limit(limite)
    )
    return [_vers_schema(m, p) for m, p in lignes]


def enregistrer(session: Session, donnees: schemas.MouvementCreation) -> schemas.Mouvement:
    produit = session.get(Produit, donnees.produit_id)
    if produit is None:
        raise ErreurMetier(422, "VALIDATION", "Certains champs ne sont pas valides.", {"produit_id": "Produit inconnu."})
    mouvement = appliquer_mouvement(session, produit, TypeMouvement(donnees.type), donnees.quantite, donnees.motif)
    valider(session)
    session.refresh(mouvement)
    return _vers_schema(mouvement, produit)
