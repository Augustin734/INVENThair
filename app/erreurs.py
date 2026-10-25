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


def _message_fr(err: dict[str, Any]) -> str:
    """Traduit les erreurs Pydantic les plus courantes ; le front les affiche telles quelles."""
    type_, ctx = err.get("type", ""), err.get("ctx") or {}
    if type_ == "value_error":
        return str(ctx.get("error", err.get("msg", "Valeur invalide")))
    messages = {
        "missing": "Champ obligatoire.",
        "extra_forbidden": "Ce champ n'est pas modifiable ici.",
        "greater_than_equal": "Doit être supérieur ou égal à {ge}.",
        "greater_than": "Doit être supérieur à {gt}.",
        "less_than_equal": "Doit être inférieur ou égal à {le}.",
        "less_than": "Doit être inférieur à {lt}.",
        "string_too_short": "Ne peut pas être vide.",
        "string_too_long": "Trop long ({max_length} caractères maximum).",
        "string_pattern_mismatch": "Format invalide.",
        "int_parsing": "Doit être un nombre entier.",
        "int_from_float": "Doit être un nombre entier.",
        "int_type": "Doit être un nombre entier.",
        "float_parsing": "Doit être un nombre.",
        "float_type": "Doit être un nombre.",
        "bool_parsing": "Doit valoir vrai ou faux.",
        "string_type": "Doit être un texte.",
        "list_type": "Doit être une liste.",
        "enum": "Valeur possible : {expected}.",
        "literal_error": "Valeur possible : {expected}.",
        "json_invalid": "Le corps de la requête n'est pas du JSON valide.",
    }
    modele = messages.get(type_)
    if modele is None:
        return err.get("msg", "Valeur invalide")
    try:
        return modele.format(**ctx)
    except (KeyError, IndexError):
        return modele


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
            details.setdefault(_champ(tuple(err.get("loc", ()))), _message_fr(err))
        return reponse_erreur(422, "VALIDATION", "Certains champs ne sont pas valides.", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = CODES_HTTP.get(exc.status_code, ("ERREUR_HTTP", str(exc.detail)))
        return reponse_erreur(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def _inattendue(_: Request, exc: Exception) -> JSONResponse:
        journal.exception("Erreur inattendue", exc_info=exc)
        return reponse_erreur(500, "ERREUR_INTERNE", "Oups, une erreur inattendue. Le détail est dans logs/inventhair.log.")
