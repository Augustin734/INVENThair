from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session, select

from app import schemas
from app.config import Reglages, obtenir_reglages
from app.database import obtenir_session
from app.models import Fournisseur, maintenant
from app.erreurs import ErreurMetier
from app.services import exports, liste_achat, mail
from app.services.produits import vers_schema

router = APIRouter(tags=["Alertes et liste d'achat"])
SessionDB = Annotated[Session, Depends(obtenir_session)]


@router.get("/alertes", response_model=list[schemas.Produit], summary="Produits sous seuil")
def alertes(session: SessionDB):
    return [vers_schema(p) for p in liste_achat.produits_en_alerte(session)]


@router.get("/liste-achat", response_model=schemas.ListeAchat, summary="Liste groupée par fournisseur")
def generer(session: SessionDB):
    return liste_achat.generer(session)


def _emails_fournisseurs(session: Session) -> dict[int, str]:
    return {f.id: f.email for f in session.exec(select(Fournisseur)) if f.email}


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
        contenu = exports.generer_pdf(liste, moment, _emails_fournisseurs(session))
    nom = exports.nom_fichier(moment, format_)
    return Response(content=contenu, media_type=FORMATS[format_], headers={"Content-Disposition": f'attachment; filename="{nom}"'})


@router.post(
    "/liste-achat/envoyer",
    response_model=schemas.EnvoiConfirme,
    status_code=202,
    responses=schemas.erreurs(502),
    summary="Envoyer la liste (éventuellement retouchée) par mail, PDF en pièce jointe",
)
def envoyer(donnees: schemas.EnvoiListe, session: SessionDB, reglages: Annotated[Reglages, Depends(obtenir_reglages)]):
    nb = sum(len(g.lignes) for g in exports.a_commander(donnees.liste))
    if nb == 0:
        raise ErreurMetier(422, "VALIDATION", "La liste est vide : rien à envoyer.", {"liste": "Aucun produit à commander."})
    moment = maintenant()
    pdf = exports.generer_pdf(donnees.liste, moment, _emails_fournisseurs(session))
    mail.envoyer(reglages, mail.composer(reglages, donnees.destinataire, donnees.liste, pdf, moment))
    return schemas.EnvoiConfirme(destinataire=donnees.destinataire, nb_produits=nb, envoye_le=moment)
