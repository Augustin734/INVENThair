from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app import schemas
from app.database import obtenir_session
from app.services import mouvements

router = APIRouter(prefix="/mouvements", tags=["Mouvements"])
SessionDB = Annotated[Session, Depends(obtenir_session)]


@router.get("", response_model=list[schemas.Mouvement], responses=schemas.erreurs(), summary="Derniers mouvements, tous produits")
def derniers(session: SessionDB, limite: Annotated[int, Query(ge=1, le=100)] = 5):
    return mouvements.derniers(session, limite)


@router.post("", response_model=schemas.Mouvement, status_code=201, responses=schemas.erreurs(409), summary="Entrée / sortie")
def enregistrer(donnees: schemas.MouvementCreation, session: SessionDB):
    return mouvements.enregistrer(session, donnees)
