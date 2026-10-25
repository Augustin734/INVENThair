"""Inventaires : ouverture, comptage au fil de l'eau, validation, annulation (US8–US10).

Règles (docs/cadrage.md § 2) :
- à l'ouverture, une ligne par produit actif avec qte_theorique = stock_actuel ;
- à chaque saisie, qte_theorique est remis au stock du moment : l'écart compare
  le comptage au stock au moment du comptage, même si des mouvements ont eu lieu
  depuis l'ouverture ;
- la validation crée un ajustement de valeur `ecart` par ligne comptée avec écart,
  donc les mouvements faits après le comptage d'une ligne sont conservés.
"""

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app import schemas
from app.erreurs import ErreurMetier
from app.models import Inventaire, LigneInventaire, Produit, StatutInventaire, TypeMouvement, maintenant
from app.services.commun import obtenir_ou_404, valider
from app.services.stock import DECIMALES, appliquer_mouvement
from app.services.textes import cle_tri


def _ecart(ligne: LigneInventaire) -> float | None:
    return None if ligne.ecart is None else round(ligne.ecart, DECIMALES)


def _lignes(session: Session, inventaire_id: int) -> list[tuple[LigneInventaire, Produit]]:
    resultat = session.exec(
        select(LigneInventaire, Produit)
        .join(Produit, Produit.id == LigneInventaire.produit_id)
        .where(LigneInventaire.inventaire_id == inventaire_id)
    )
    return sorted(resultat.all(), key=lambda lp: (cle_tri(lp[1].nom), lp[1].id))


def _ligne_vers_schema(ligne: LigneInventaire, produit: Produit) -> schemas.LigneInventaire:
    return schemas.LigneInventaire(
        id=ligne.id,
        produit_id=produit.id,
        produit_nom=produit.nom,
        unite=produit.unite,
        qte_theorique=ligne.qte_theorique,
        qte_comptee=ligne.qte_comptee,
        ecart=_ecart(ligne),
        compte_le=ligne.compte_le,
    )


def _resume(inventaire: Inventaire, lignes: list[LigneInventaire]) -> dict:
    return {
        **inventaire.model_dump(),
        "nb_lignes": len(lignes),
        "nb_comptees": sum(1 for l in lignes if l.qte_comptee is not None),
        "nb_ecarts": sum(1 for l in lignes if _ecart(l) not in (None, 0)),
    }


def _detail(session: Session, inventaire: Inventaire) -> schemas.InventaireDetail:
    lignes = _lignes(session, inventaire.id)
    return schemas.InventaireDetail(
        **_resume(inventaire, [l for l, _ in lignes]),
        lignes=[_ligne_vers_schema(l, p) for l, p in lignes],
    )


def _obtenir_brouillon(session: Session, inventaire_id: int) -> Inventaire:
    inventaire = obtenir_ou_404(session, Inventaire, inventaire_id, "Inventaire")
    if inventaire.statut is not StatutInventaire.brouillon:
        etat = "validé" if inventaire.statut is StatutInventaire.valide else "annulé"
        raise ErreurMetier(
            409,
            "INVENTAIRE_VERROUILLE",
            f"L'inventaire N°{inventaire.id} est {etat} : il ne peut plus être modifié.",
            {"inventaire_id": inventaire.id, "statut": inventaire.statut.value},
        )
    return inventaire


def _brouillon_existant(session: Session) -> ErreurMetier | None:
    brouillon = session.exec(select(Inventaire).where(Inventaire.statut == StatutInventaire.brouillon)).first()
    if brouillon is None:
        return None
    return ErreurMetier(
        409,
        "INVENTAIRE_EN_COURS",
        f"L'inventaire N°{brouillon.id} est déjà en cours : reprends-le ou annule-le avant d'en lancer un autre.",
        {"inventaire_id": brouillon.id},
    )


def lister(session: Session) -> list[schemas.Inventaire]:
    inventaires = session.exec(select(Inventaire).order_by(Inventaire.cree_le.desc(), Inventaire.id.desc())).all()
    toutes = session.exec(select(LigneInventaire)).all()
    par_inventaire: dict[int, list[LigneInventaire]] = {}
    for ligne in toutes:
        par_inventaire.setdefault(ligne.inventaire_id, []).append(ligne)
    return [schemas.Inventaire(**_resume(i, par_inventaire.get(i.id, []))) for i in inventaires]


def detail(session: Session, inventaire_id: int) -> schemas.InventaireDetail:
    return _detail(session, obtenir_ou_404(session, Inventaire, inventaire_id, "Inventaire"))


def ouvrir(session: Session, donnees: schemas.InventaireOuverture) -> schemas.InventaireDetail:
    if (erreur := _brouillon_existant(session)) is not None:
        raise erreur
    inventaire = Inventaire(commentaire=donnees.commentaire)
    session.add(inventaire)
    try:
        session.flush()
    except IntegrityError:  # un autre onglet a ouvert un brouillon entre-temps
        session.rollback()
        raise _brouillon_existant(session) or ErreurMetier(409, "INVENTAIRE_EN_COURS", "Un inventaire est déjà en cours.")
    for produit in session.exec(select(Produit).where(Produit.archive.is_(False))):
        session.add(LigneInventaire(inventaire_id=inventaire.id, produit_id=produit.id, qte_theorique=produit.stock_actuel))
    valider(session)
    session.refresh(inventaire)
    return _detail(session, inventaire)


def saisir(session: Session, inventaire_id: int, ligne_id: int, qte_comptee: float | None) -> schemas.LigneInventaire:
    _obtenir_brouillon(session, inventaire_id)
    ligne = session.get(LigneInventaire, ligne_id)
    if ligne is None or ligne.inventaire_id != inventaire_id:
        raise ErreurMetier(404, "INTROUVABLE", "Ligne d'inventaire introuvable.", {"ligne_id": ligne_id})
    produit = session.get(Produit, ligne.produit_id)

    ligne.qte_theorique = produit.stock_actuel
    ligne.qte_comptee = None if qte_comptee is None else round(qte_comptee, DECIMALES)
    ligne.compte_le = None if qte_comptee is None else maintenant()
    session.add(ligne)
    valider(session)
    session.refresh(ligne)
    return _ligne_vers_schema(ligne, produit)


def valider_inventaire(session: Session, inventaire_id: int, garder_theorique_si_vide: bool) -> schemas.InventaireDetail:
    inventaire = _obtenir_brouillon(session, inventaire_id)
    lignes = _lignes(session, inventaire.id)

    non_comptees = [p.nom for l, p in lignes if l.qte_comptee is None]
    if non_comptees and not garder_theorique_si_vide:
        nb = len(non_comptees)
        raise ErreurMetier(
            409,
            "LIGNES_NON_COMPTEES",
            f"Il reste {nb} produit{'s' if nb > 1 else ''} à compter. "
            "Compte-les ou coche « Garder la quantité théorique ».",
            {"nb_non_comptees": nb, "produits": non_comptees},
        )

    a_ajuster = [(l, p) for l, p in lignes if _ecart(l) not in (None, 0)]

    # Tout vérifier avant d'écrire, pour signaler toutes les lignes fautives d'un coup.
    negatifs = [
        {"ligne_id": l.id, "produit_id": p.id, "produit_nom": p.nom, "stock_actuel": p.stock_actuel, "ecart": _ecart(l)}
        for l, p in a_ajuster
        if round(p.stock_actuel + _ecart(l), DECIMALES) < 0
    ]
    if negatifs:
        noms = ", ".join(n["produit_nom"] for n in negatifs)
        raise ErreurMetier(
            409,
            "STOCK_INSUFFISANT",
            f"Des sorties ont été faites après le comptage : l'ajustement rendrait le stock négatif pour {noms}. Recompte ces produits.",
            {"lignes": negatifs},
        )

    for ligne, produit in a_ajuster:
        appliquer_mouvement(session, produit, TypeMouvement.ajustement, _ecart(ligne), f"Inventaire N°{inventaire.id}", inventaire.id)
    inventaire.statut = StatutInventaire.valide
    inventaire.valide_le = maintenant()
    session.add(inventaire)
    valider(session)
    session.refresh(inventaire)
    return _detail(session, inventaire)


def annuler(session: Session, inventaire_id: int) -> schemas.InventaireDetail:
    inventaire = _obtenir_brouillon(session, inventaire_id)
    inventaire.statut = StatutInventaire.annule
    session.add(inventaire)
    valider(session)
    session.refresh(inventaire)
    return _detail(session, inventaire)
