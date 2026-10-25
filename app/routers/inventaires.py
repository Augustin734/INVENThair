from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app import schemas
from app.database import obtenir_session
from app.services import inventaires

router = APIRouter(prefix="/inventaires", tags=["Inventaires"])
SessionDB = Annotated[Session, Depends(obtenir_session)]


@router.get("", response_model=list[schemas.Inventaire], summary="Lister, du plus récent au plus ancien")
def lister(session: SessionDB):
    return inventaires.lister(session)


@router.post("", response_model=schemas.InventaireDetail, status_code=201, responses=schemas.erreurs(409), summary="Ouvrir un brouillon")
def ouvrir(session: SessionDB, donnees: schemas.InventaireOuverture | None = None):
    return inventaires.ouvrir(session, donnees or schemas.InventaireOuverture())


@router.get("/{inventaire_id}", response_model=schemas.InventaireDetail, responses=schemas.erreurs(404), summary="Détail avec lignes")
def detail(inventaire_id: int, session: SessionDB):
    return inventaires.detail(session, inventaire_id)


@router.patch(
    "/{inventaire_id}/lignes/{ligne_id}",
    response_model=schemas.LigneInventaire,
    responses=schemas.erreurs(404, 409),
    summary="Saisir une quantité comptée (null efface)",
)
def saisir(inventaire_id: int, ligne_id: int, donnees: schemas.SaisieComptage, session: SessionDB):
    return inventaires.saisir(session, inventaire_id, ligne_id, donnees.qte_comptee)


@router.post("/{inventaire_id}/valider", response_model=schemas.InventaireDetail, responses=schemas.erreurs(404, 409), summary="Valider et créer les ajustements")
def valider(inventaire_id: int, session: SessionDB, donnees: schemas.ValidationInventaire | None = None):
    return inventaires.valider_inventaire(session, inventaire_id, (donnees or schemas.ValidationInventaire()).garder_theorique_si_vide)


@router.post("/{inventaire_id}/annuler", response_model=schemas.InventaireDetail, responses=schemas.erreurs(404, 409), summary="Annuler un brouillon")
def annuler(inventaire_id: int, session: SessionDB):
    return inventaires.annuler(session, inventaire_id)
