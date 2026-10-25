"""Point d'entrée : `uvicorn app.main:app`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import lire_reglages
from app.database import creer_moteur, initialiser_base
from app.erreurs import installer_gestionnaires
from app.routers import categories, fournisseurs, inventaires, liste_achat, mouvements, outils, pages, produits, sante

DOSSIER_APP = Path(__file__).resolve().parent
PREFIXE_API = "/api/v1"


def creer_app(chemin_base: Path | None = None) -> FastAPI:
    chemin = chemin_base or lire_reglages().chemin_base

    @asynccontextmanager
    async def cycle_de_vie(app: FastAPI) -> AsyncIterator[None]:
        app.state.chemin_base = chemin
        app.state.moteur = creer_moteur(chemin)
        initialiser_base(app.state.moteur)
        yield
        app.state.moteur.dispose()

    app = FastAPI(
        title="INVENThair",
        description="Gestion de stock de l'onglerie. Seul point d'accès aux données.",
        version="0.1.0",
        lifespan=cycle_de_vie,
    )
    installer_gestionnaires(app)
    app.include_router(sante.router, prefix=PREFIXE_API)
    app.include_router(categories.router, prefix=PREFIXE_API)
    app.include_router(fournisseurs.router, prefix=PREFIXE_API)
    app.include_router(produits.router, prefix=PREFIXE_API)
    app.include_router(mouvements.router, prefix=PREFIXE_API)
    app.include_router(inventaires.router, prefix=PREFIXE_API)
    app.include_router(liste_achat.router, prefix=PREFIXE_API)
    app.include_router(outils.router, prefix=PREFIXE_API)

    app.include_router(pages.router)
    app.mount("/static", StaticFiles(directory=DOSSIER_APP / "static"), name="static")

    return app


app = creer_app()
