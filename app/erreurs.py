"""Format d'erreur unique : {"erreur": {"code", "message", "details"}} (docs/cadrage.md § 4)."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

journal = logging.getLogger("inventhair")

# Codes techniques, hors liste métier du cadrage : renvoyés par le framework, pas par les services.
CODES_HTTP = {
    404: ("INTROUVABLE", "Ce que tu cherches n'existe pas."),
    405: ("METHODE_NON_AUTORISEE", "Cette action n'est pas possible à cette adresse."),
}


class ErreurMetier(Exception):
    """Levée par les services ; transformée en réponse JSON au format unique."""

    def __init__(self, statut: int, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.statut = statut
        self.code = code
        self.message = message
        self.details = details or {}


def reponse_erreur(statut: int, code: str, message: str, details: dict[str, Any] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=statut,
        content={"erreur": {"code": code, "message": message, "details": details or {}}},
    )


def _champ(loc: tuple) -> str:
    morceaux = [str(m) for m in loc if m not in ("body", "query", "path")]
    return ".".join(morceaux) or "requete"


def installer_gestionnaires(app: FastAPI) -> None:
    @app.exception_handler(ErreurMetier)
    async def _metier(_: Request, exc: ErreurMetier) -> JSONResponse:
        return reponse_erreur(exc.statut, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details: dict[str, str] = {}
        for err in exc.errors():
            details.setdefault(_champ(tuple(err.get("loc", ()))), err.get("msg", "Valeur invalide"))
        return reponse_erreur(422, "VALIDATION", "Certains champs ne sont pas valides.", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = CODES_HTTP.get(exc.status_code, ("ERREUR_HTTP", str(exc.detail)))
        return reponse_erreur(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def _inattendue(_: Request, exc: Exception) -> JSONResponse:
        journal.exception("Erreur inattendue", exc_info=exc)
        return reponse_erreur(500, "ERREUR_INTERNE", "Oups, une erreur inattendue. Le détail est dans logs/inventhair.log.")
