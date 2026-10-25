"""Fournisseurs : carnet d'adresses utilisé pour grouper la liste d'achat (US16b)."""

from sqlalchemy import func
from sqlmodel import Session, select

from app import schemas
from app.erreurs import ErreurMetier
from app.models import Fournisseur, Produit
from app.services.commun import nom_deja_pris, obtenir_ou_404, valider
from app.services.textes import cle_tri, cle_unicite


def _nb_produits(session: Session) -> dict[int, int]:
    lignes = session.exec(
        select(Produit.fournisseur_id, func.count())
        .where(Produit.fournisseur_id.is_not(None))
        .group_by(Produit.fournisseur_id)
    )
    return dict(lignes.all())


def _vers_schema(fournisseur: Fournisseur, nb_produits: int) -> schemas.Fournisseur:
    return schemas.Fournisseur(**fournisseur.model_dump(), nb_produits=nb_produits)


def _verifier_nom_libre(session: Session, nom: str, sauf_id: int | None = None) -> None:
    cle = cle_unicite(nom)
    if any(f.id != sauf_id and cle_unicite(f.nom) == cle for f in session.exec(select(Fournisseur))):
        raise nom_deja_pris(nom)


def lister(session: Session) -> list[schemas.Fournisseur]:
    nb = _nb_produits(session)
    fournisseurs = sorted(session.exec(select(Fournisseur)), key=lambda f: cle_tri(f.nom))
    return [_vers_schema(f, nb.get(f.id, 0)) for f in fournisseurs]


def detail(session: Session, fournisseur: Fournisseur) -> schemas.Fournisseur:
    return _vers_schema(fournisseur, _nb_produits(session).get(fournisseur.id, 0))


def creer(session: Session, donnees: schemas.FournisseurCreation) -> schemas.Fournisseur:
    _verifier_nom_libre(session, donnees.nom)
    fournisseur = Fournisseur(**donnees.model_dump())
    session.add(fournisseur)
    valider(session)
    session.refresh(fournisseur)
    return detail(session, fournisseur)


def modifier(session: Session, fournisseur_id: int, donnees: schemas.FournisseurModification) -> schemas.Fournisseur:
    fournisseur = obtenir_ou_404(session, Fournisseur, fournisseur_id, "Fournisseur")
    changements = donnees.changements()
    if "nom" in changements:
        _verifier_nom_libre(session, donnees.nom, sauf_id=fournisseur.id)
    for champ, valeur in changements.items():
        setattr(fournisseur, champ, valeur)
    session.add(fournisseur)
    valider(session)
    session.refresh(fournisseur)
    return detail(session, fournisseur)


def supprimer(session: Session, fournisseur_id: int) -> None:
    fournisseur = obtenir_ou_404(session, Fournisseur, fournisseur_id, "Fournisseur")
    nb = _nb_produits(session).get(fournisseur.id, 0)
    if nb > 0:
        nb_archives = session.exec(
            select(func.count()).where(Produit.fournisseur_id == fournisseur.id, Produit.archive.is_(True))
        ).one()
        precision = f" (dont {nb_archives} archivé{'s' if nb_archives > 1 else ''})" if nb_archives else ""
        raise ErreurMetier(
            409,
            "RESSOURCE_UTILISEE",
            f"{fournisseur.nom} a encore {nb} produit{'s' if nb > 1 else ''}{precision}. "
            f"Change {'leur' if nb > 1 else 'son'} fournisseur avant de le supprimer.",
            {"nb_produits": nb, "nb_archives": nb_archives},
        )
    session.delete(fournisseur)
    valider(session)
