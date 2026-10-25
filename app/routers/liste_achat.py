from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app import schemas
from app.database import obtenir_session
from app.services import liste_achat
from app.services.produits import vers_schema

router = APIRouter(tags=["Alertes et liste d'achat"])
SessionDB = Annotated[Session, Depends(obtenir_session)]


@router.get("/alertes", response_model=list[schemas.Produit], summary="Produits sous seuil")
def alertes(session: SessionDB):
    return [vers_schema(p) for p in liste_achat.produits_en_alerte(session)]


@router.get("/liste-achat", response_model=schemas.ListeAchat, summary="Liste groupée par fournisseur")
def generer(session: SessionDB):
    return liste_achat.generer(session)
