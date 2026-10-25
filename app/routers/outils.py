from fastapi import APIRouter, Request

from app import schemas
from app.services import sauvegarde

router = APIRouter(tags=["Outils"])


@router.post("/backup", response_model=schemas.Sauvegarde, status_code=201, summary="Copie datée de la base dans backups/")
def sauvegarder(request: Request):
    fichier = sauvegarde.sauvegarder(request.app.state.chemin_base)
    return schemas.Sauvegarde(fichier=fichier.name)
