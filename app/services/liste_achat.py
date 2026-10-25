"""Alertes et liste d'achat (US11, US12)."""

from sqlmodel import Session, select

from app import schemas
from app.models import Fournisseur, Produit, maintenant
from app.services.produits import en_alerte
from app.services.textes import cle_tri

SANS_FOURNISSEUR = "Sans fournisseur"


def produits_en_alerte(session: Session) -> list[Produit]:
    produits = [p for p in session.exec(select(Produit).where(Produit.archive.is_(False))) if en_alerte(p)]
    return sorted(produits, key=lambda p: (cle_tri(p.nom), p.id))


def generer(session: Session) -> schemas.ListeAchat:
    """Produits en alerte groupés par fournisseur (par nom), « Sans fournisseur » en dernier."""
    noms = {f.id: f.nom for f in session.exec(select(Fournisseur))}
    groupes: dict[int | None, list[schemas.LigneAchat]] = {}
    for p in produits_en_alerte(session):
        groupes.setdefault(p.fournisseur_id, []).append(
            schemas.LigneAchat(
                produit_id=p.id, nom=p.nom, unite=p.unite, stock_actuel=p.stock_actuel, seuil_alerte=p.seuil_alerte, quantite=p.qte_reappro
            )
        )
    ordre = sorted(groupes, key=lambda fid: (fid is None, cle_tri(noms.get(fid, ""))))
    return schemas.ListeAchat(
        genere_le=maintenant(),
        fournisseurs=[
            schemas.GroupeFournisseur(fournisseur_id=fid, nom=noms[fid] if fid is not None else SANS_FOURNISSEUR, lignes=groupes[fid])
            for fid in ordre
        ],
    )
