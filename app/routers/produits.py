from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app import schemas
from app.database import obtenir_session
from app.services import mouvements, produits

router = APIRouter(prefix="/produits", tags=["Produits"])
SessionDB = Annotated[Session, Depends(obtenir_session)]


@router.get("", response_model=list[schemas.Produit], responses=schemas.erreurs(), summary="Lister avec filtres, tri par nom")
def lister(
    session: SessionDB,
    categorie_id: int | None = None,
    q: Annotated[str | None, Query(description="Recherche dans le nom et la référence")] = None,
    archive: bool = False,
    en_alerte: bool | None = None,
):
    return produits.lister(session, categorie_id, q, archive, en_alerte)


@router.post("", response_model=schemas.Produit, status_code=201, responses=schemas.erreurs(), summary="Créer (+ stock_initial optionnel)")
def creer(donnees: schemas.ProduitCreation, session: SessionDB):
    return produits.creer(session, donnees)


@router.get("/{produit_id}", response_model=schemas.Produit, responses=schemas.erreurs(404), summary="Détail")
def detail(produit_id: int, session: SessionDB):
    return produits.vers_schema(produits.obtenir(session, produit_id))


@router.patch("/{produit_id}", response_model=schemas.Produit, responses=schemas.erreurs(404), summary="Modifier (sans stock_actuel)")
def modifier(produit_id: int, donnees: schemas.ProduitModification, session: SessionDB):
    return produits.modifier(session, produit_id, donnees)


@router.post("/{produit_id}/archiver", response_model=schemas.Produit, responses=schemas.erreurs(404), summary="Archiver, avec un motif facultatif")
def archiver(produit_id: int, session: SessionDB, donnees: schemas.Archivage | None = None):
    return produits.archiver(session, produit_id, donnees.motif if donnees else None)


@router.post("/{produit_id}/desarchiver", response_model=schemas.Produit, responses=schemas.erreurs(404), summary="Désarchiver")
def desarchiver(produit_id: int, session: SessionDB):
    return produits.desarchiver(session, produit_id)


@router.get("/{produit_id}/mouvements", response_model=list[schemas.Mouvement], responses=schemas.erreurs(404), summary="Historique, du plus récent au plus ancien")
def historique(produit_id: int, session: SessionDB):
    return mouvements.historique(session, produit_id)
