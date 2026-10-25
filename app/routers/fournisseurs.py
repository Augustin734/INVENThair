from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app import schemas
from app.database import obtenir_session
from app.services import fournisseurs

router = APIRouter(prefix="/fournisseurs", tags=["Fournisseurs"])
SessionDB = Annotated[Session, Depends(obtenir_session)]


@router.get("", response_model=list[schemas.Fournisseur], summary="Lister par nom (avec nb_produits)")
def lister(session: SessionDB):
    return fournisseurs.lister(session)


@router.post("", response_model=schemas.Fournisseur, status_code=201, summary="Créer")
def creer(donnees: schemas.FournisseurCreation, session: SessionDB):
    return fournisseurs.creer(session, donnees)


@router.patch("/{fournisseur_id}", response_model=schemas.Fournisseur, summary="Modifier")
def modifier(fournisseur_id: int, donnees: schemas.FournisseurModification, session: SessionDB):
    return fournisseurs.modifier(session, fournisseur_id, donnees)


@router.delete("/{fournisseur_id}", status_code=204, summary="Supprimer (refus si utilisé)")
def supprimer(fournisseur_id: int, session: SessionDB):
    fournisseurs.supprimer(session, fournisseur_id)
    return Response(status_code=204)
