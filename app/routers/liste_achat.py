from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session, select

from app import schemas
from app.database import obtenir_session
from app.models import Fournisseur, maintenant
from app.services import exports, liste_achat
from app.services.produits import vers_schema

router = APIRouter(tags=["Alertes et liste d'achat"])
SessionDB = Annotated[Session, Depends(obtenir_session)]


@router.get("/alertes", response_model=list[schemas.Produit], summary="Produits sous seuil")
def alertes(session: SessionDB):
    return [vers_schema(p) for p in liste_achat.produits_en_alerte(session)]


@router.get("/liste-achat", response_model=schemas.ListeAchat, summary="Liste groupée par fournisseur")
def generer(session: SessionDB):
    return liste_achat.generer(session)


FORMATS = {"csv": "text/csv; charset=utf-8", "pdf": "application/pdf"}


@router.post(
    "/liste-achat/export",
    response_class=Response,
    responses={200: {"description": "Fichier liste-achat-AAAA-MM-JJ", "content": {"text/csv": {}, "application/pdf": {}}}, **schemas.erreurs()},
    summary="Télécharger la liste (éventuellement retouchée) en CSV ou PDF",
)
def exporter(
    liste: schemas.ListeAchat,
    session: SessionDB,
    format_: Annotated[Literal["csv", "pdf"], Query(alias="format")],
):
    moment = maintenant()
    if format_ == "csv":
        contenu = exports.generer_csv(liste)
    else:
        emails = {f.id: f.email for f in session.exec(select(Fournisseur)) if f.email}
        contenu = exports.generer_pdf(liste, moment, emails)
    nom = exports.nom_fichier(moment, format_)
    return Response(content=contenu, media_type=FORMATS[format_], headers={"Content-Disposition": f'attachment; filename="{nom}"'})
