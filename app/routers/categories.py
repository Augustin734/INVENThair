from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session

from app import schemas
from app.database import obtenir_session
from app.services import categories

router = APIRouter(prefix="/categories", tags=["Catégories"])
SessionDB = Annotated[Session, Depends(obtenir_session)]


@router.get("", response_model=list[schemas.Categorie], summary="Lister (avec nb_produits)")
def lister(session: SessionDB):
    return categories.lister(session)


@router.post("", response_model=schemas.Categorie, status_code=201, summary="Créer")
def creer(donnees: schemas.CategorieCreation, session: SessionDB):
    return categories.creer(session, donnees)


@router.post("/reordonner", response_model=list[schemas.Categorie], summary="Réécrire l'ordre de toutes les catégories")
def reordonner(donnees: schemas.Reordonnancement, session: SessionDB):
    return categories.reordonner(session, donnees.ids)


@router.patch("/{categorie_id}", response_model=schemas.Categorie, summary="Modifier (nom, couleur, ordre)")
def modifier(categorie_id: int, donnees: schemas.CategorieModification, session: SessionDB):
    return categories.modifier(session, categorie_id, donnees)


@router.delete("/{categorie_id}", status_code=204, summary="Supprimer (fusion avec ?fusionner_vers=)")
def supprimer(
    categorie_id: int,
    session: SessionDB,
    fusionner_vers: Annotated[int | None, Query(description="Catégorie qui reçoit les produits")] = None,
):
    categories.supprimer(session, categorie_id, fusionner_vers)
    return Response(status_code=204)
