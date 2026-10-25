"""Produits : création (avec stock initial), liste filtrée, modification, archivage (US1–US4)."""

from sqlalchemy import delete
from sqlmodel import Session, select

from app import schemas
from app.erreurs import ErreurMetier
from app.models import Categorie, Fournisseur, Inventaire, LigneInventaire, Produit, StatutInventaire, TypeMouvement, maintenant
from app.services.commun import obtenir_ou_404, valider
from app.services.stock import appliquer_mouvement
from app.services.textes import cle_tri

COEF_A_SURVEILLER = 1.5


def en_alerte(produit: Produit) -> bool:
    """Alerte = produit non archivé avec stock_actuel <= seuil_alerte."""
    return not produit.archive and produit.stock_actuel <= produit.seuil_alerte


def statut(produit: Produit) -> schemas.StatutProduit:
    """Calculé sur le stock seul ; un produit archivé n'est jamais `en_alerte` pour autant."""
    if produit.stock_actuel <= produit.seuil_alerte:
        return "alerte"
    if produit.stock_actuel <= COEF_A_SURVEILLER * produit.seuil_alerte:
        return "a_surveiller"
    return "en_forme"


def vers_schema(produit: Produit) -> schemas.Produit:
    return schemas.Produit(**produit.model_dump(), en_alerte=en_alerte(produit), statut=statut(produit))


def obtenir(session: Session, produit_id: int) -> Produit:
    return obtenir_ou_404(session, Produit, produit_id, "Produit")


def _verifier_references(session: Session, categorie_id: int | None, fournisseur_id: int | None) -> None:
    details = {}
    if categorie_id is not None and session.get(Categorie, categorie_id) is None:
        details["categorie_id"] = "Catégorie inconnue."
    if fournisseur_id is not None and session.get(Fournisseur, fournisseur_id) is None:
        details["fournisseur_id"] = "Fournisseur inconnu."
    if details:
        raise ErreurMetier(422, "VALIDATION", "Certains champs ne sont pas valides.", details)


def lister(
    session: Session,
    categorie_id: int | None = None,
    q: str | None = None,
    archive: bool = False,
    filtre_alerte: bool | None = None,
) -> list[schemas.Produit]:
    requete = select(Produit).where(Produit.archive == archive)
    if categorie_id is not None:
        requete = requete.where(Produit.categorie_id == categorie_id)
    produits = list(session.exec(requete))

    if filtre_alerte is not None:
        produits = [p for p in produits if en_alerte(p) == filtre_alerte]
    if q and q.strip():
        cherche = cle_tri(q.strip())
        produits = [p for p in produits if cherche in cle_tri(f"{p.nom} {p.reference or ''}")]

    produits.sort(key=lambda p: (cle_tri(p.nom), p.id))
    return [vers_schema(p) for p in produits]


def creer(session: Session, donnees: schemas.ProduitCreation) -> schemas.Produit:
    _verifier_references(session, donnees.categorie_id, donnees.fournisseur_id)
    produit = Produit(**donnees.model_dump(exclude={"stock_initial"}))
    session.add(produit)
    session.flush()  # attribue l'id avant le mouvement
    if donnees.stock_initial:
        appliquer_mouvement(session, produit, TypeMouvement.entree, donnees.stock_initial, "Stock initial")
    valider(session)
    session.refresh(produit)
    return vers_schema(produit)


def modifier(session: Session, produit_id: int, donnees: schemas.ProduitModification) -> schemas.Produit:
    produit = obtenir(session, produit_id)
    changements = donnees.changements()
    _verifier_references(session, changements.get("categorie_id"), changements.get("fournisseur_id"))
    for champ, valeur in changements.items():
        setattr(produit, champ, valeur)
    produit.maj_le = maintenant()
    session.add(produit)
    valider(session)
    session.refresh(produit)
    return vers_schema(produit)


def archiver(session: Session, produit_id: int, motif: str | None) -> schemas.Produit:
    produit = obtenir(session, produit_id)
    if not produit.archive:
        produit.archive = True
        produit.archive_le = maintenant()
        produit.archive_motif = motif
        # Le produit sort aussi d'un inventaire en cours (les inventaires validés gardent leur ligne).
        brouillons = select(Inventaire.id).where(Inventaire.statut == StatutInventaire.brouillon)
        session.exec(
            delete(LigneInventaire).where(
                LigneInventaire.produit_id == produit.id,
                LigneInventaire.inventaire_id.in_(brouillons),
            )
        )
    elif motif is not None:
        produit.archive_motif = motif
    produit.maj_le = maintenant()
    session.add(produit)
    valider(session)
    session.refresh(produit)
    return vers_schema(produit)


def desarchiver(session: Session, produit_id: int) -> schemas.Produit:
    produit = obtenir(session, produit_id)
    if produit.archive:
        produit.archive = False
        produit.archive_le = None
        produit.archive_motif = None
        produit.maj_le = maintenant()
        session.add(produit)
        valider(session)
        session.refresh(produit)
    return vers_schema(produit)
