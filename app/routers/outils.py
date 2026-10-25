from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app import schemas
from app.config import Reglages, obtenir_reglages
from app.services import sauvegarde

router = APIRouter(tags=["Outils"])


@router.post("/backup", response_model=schemas.Sauvegarde, status_code=201, summary="Copie datée de la base dans backups/")
def sauvegarder(request: Request):
    fichier = sauvegarde.sauvegarder(request.app.state.chemin_base)
    return schemas.Sauvegarde(fichier=fichier.name)


@router.get("/parametres", response_model=schemas.Parametres, summary="Réglages utiles au front (jamais les identifiants SMTP)")
def parametres(reglages: Annotated[Reglages, Depends(obtenir_reglages)]):
    return schemas.Parametres(
        mail_destinataire_defaut=reglages.mail_destinataire_defaut or None,
        envoi_mail_configure=reglages.envoi_mail_configure,
    )
