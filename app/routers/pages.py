"""Pages HTML. Elles ne servent que la structure : les données viennent de l'API, côté navigateur."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

DOSSIER_GABARITS = Path(__file__).resolve().parent.parent / "templates"

router = APIRouter(include_in_schema=False, default_response_class=HTMLResponse)
gabarits = Jinja2Templates(directory=DOSSIER_GABARITS)


def _page(request: Request, gabarit: str, page: str, titre: str, **contexte) -> HTMLResponse:
    return gabarits.TemplateResponse(
        request, gabarit, {"page": page, "titre": titre, "version": request.app.version, **contexte}
    )


@router.get("/")
def accueil(request: Request):
    return _page(request, "accueil.html", "accueil", "Accueil")


@router.get("/produits")
def produits(request: Request):
    return _page(request, "produits.html", "produits", "Produits")


@router.get("/produits/{produit_id}")
def fiche_produit(request: Request, produit_id: int):
    return _page(request, "fiche_produit.html", "produits", "Fiche produit", produit_id=produit_id)
