"""Catégories : création, renommage, couleur, ordre, suppression avec fusion (US16)."""

from sqlalchemy import func, update
from sqlmodel import Session, select

from app import schemas
from app.erreurs import ErreurMetier
from app.models import Categorie, Produit, maintenant
from app.services.commun import nom_deja_pris, obtenir_ou_404, valider
from app.services.textes import cle_unicite


def _nb_produits(session: Session) -> dict[int, int]:
    """Archivés compris : ils bloquent aussi la suppression."""
    lignes = session.exec(select(Produit.categorie_id, func.count()).group_by(Produit.categorie_id))
    return dict(lignes.all())


def _vers_schema(categorie: Categorie, nb_produits: int) -> schemas.Categorie:
    return schemas.Categorie(
        id=categorie.id,
        nom=categorie.nom,
        couleur=schemas.Couleur(r=categorie.couleur_r, g=categorie.couleur_g, b=categorie.couleur_b, a=categorie.couleur_a),
        ordre=categorie.ordre,
        nb_produits=nb_produits,
        cree_le=categorie.cree_le,
    )


def _toutes(session: Session) -> list[Categorie]:
    return list(session.exec(select(Categorie).order_by(Categorie.ordre, Categorie.id)))


def _verifier_nom_libre(session: Session, nom: str, sauf_id: int | None = None) -> None:
    cle = cle_unicite(nom)
    if any(c.id != sauf_id and cle_unicite(c.nom) == cle for c in _toutes(session)):
        raise nom_deja_pris(nom)


def _appliquer_couleur(categorie: Categorie, couleur: schemas.Couleur) -> None:
    categorie.couleur_r, categorie.couleur_g, categorie.couleur_b, categorie.couleur_a = couleur.r, couleur.g, couleur.b, couleur.a


def lister(session: Session) -> list[schemas.Categorie]:
    nb = _nb_produits(session)
    return [_vers_schema(c, nb.get(c.id, 0)) for c in _toutes(session)]


def detail(session: Session, categorie: Categorie) -> schemas.Categorie:
    return _vers_schema(categorie, _nb_produits(session).get(categorie.id, 0))


def creer(session: Session, donnees: schemas.CategorieCreation) -> schemas.Categorie:
    _verifier_nom_libre(session, donnees.nom)
    ordre_max = session.exec(select(func.max(Categorie.ordre))).one() or 0
    categorie = Categorie(nom=donnees.nom, couleur_r=0, couleur_g=0, couleur_b=0, ordre=ordre_max + 1)
    _appliquer_couleur(categorie, donnees.couleur)
    session.add(categorie)
    valider(session)
    session.refresh(categorie)
    return detail(session, categorie)


def modifier(session: Session, categorie_id: int, donnees: schemas.CategorieModification) -> schemas.Categorie:
    categorie = obtenir_ou_404(session, Categorie, categorie_id, "Catégorie")
    changements = donnees.changements()
    if "nom" in changements:
        _verifier_nom_libre(session, donnees.nom, sauf_id=categorie.id)
        categorie.nom = donnees.nom
    if "couleur" in changements:
        _appliquer_couleur(categorie, donnees.couleur)
    if "ordre" in changements:
        categorie.ordre = donnees.ordre
    session.add(categorie)
    valider(session)
    session.refresh(categorie)
    return detail(session, categorie)


def reordonner(session: Session, ids: list[int]) -> list[schemas.Categorie]:
    categories = {c.id: c for c in _toutes(session)}
    if len(ids) != len(set(ids)):
        raise ErreurMetier(422, "VALIDATION", "Une catégorie apparaît deux fois.", {"ids": "Chaque catégorie une seule fois."})
    if set(ids) != set(categories):
        manquantes = sorted(set(categories) - set(ids))
        inconnues = sorted(set(ids) - set(categories))
        raise ErreurMetier(
            422,
            "VALIDATION",
            "La liste doit contenir toutes les catégories, et seulement elles.",
            {"ids": "Liste incomplète ou inconnue.", "manquantes": manquantes, "inconnues": inconnues},
        )
    for ordre, id_ in enumerate(ids, start=1):
        categories[id_].ordre = ordre
        session.add(categories[id_])
    valider(session)
    return lister(session)


def supprimer(session: Session, categorie_id: int, fusionner_vers: int | None) -> None:
    categorie = obtenir_ou_404(session, Categorie, categorie_id, "Catégorie")
    nb = _nb_produits(session).get(categorie.id, 0)

    if fusionner_vers is not None:
        if fusionner_vers == categorie.id:
            raise ErreurMetier(422, "VALIDATION", "Choisis une autre catégorie que celle à supprimer.", {"fusionner_vers": "Doit être une autre catégorie."})
        destination = obtenir_ou_404(session, Categorie, fusionner_vers, "Catégorie de destination")
        session.exec(
            update(Produit)
            .where(Produit.categorie_id == categorie.id)
            .values(categorie_id=destination.id, maj_le=maintenant())
        )
    elif nb > 0:
        raise ErreurMetier(
            409,
            "RESSOURCE_UTILISEE",
            f"« {categorie.nom} » contient {nb} produit{'s' if nb > 1 else ''}. Choisis où les ranger avant de la supprimer.",
            {"nb_produits": nb},
        )

    session.delete(categorie)
    valider(session)
