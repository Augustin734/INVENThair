"""Seul point de passage des variations de stock (CLAUDE.md, docs/cadrage.md § 2)."""

from sqlmodel import Session

from app.erreurs import ErreurMetier
from app.models import Mouvement, Produit, TypeMouvement, maintenant

DECIMALES = 3  # évite les restes du type 0.1 + 0.2 = 0.30000000000000004


def appliquer_mouvement(
    session: Session,
    produit: Produit,
    type_: TypeMouvement,
    quantite: float,
    motif: str | None = None,
    inventaire_id: int | None = None,
) -> Mouvement:
    """Crée le mouvement et met `stock_actuel` à jour, sans valider la transaction.

    `quantite` est positive pour une entrée ou une sortie (le signe vient du type)
    et signée pour un ajustement (l'écart d'inventaire).
    """
    if produit.archive:
        raise ErreurMetier(
            409,
            "PRODUIT_ARCHIVE",
            f"« {produit.nom} » est archivé. Désarchive-le avant d'enregistrer un mouvement.",
            {"produit_id": produit.id},
        )

    if type_ is TypeMouvement.ajustement:
        variation = quantite
    elif quantite <= 0:
        raise ErreurMetier(422, "VALIDATION", "La quantité doit être positive.", {"quantite": "Doit être supérieur à 0."})
    else:
        variation = quantite if type_ is TypeMouvement.entree else -quantite

    nouveau_stock = round(produit.stock_actuel + variation, DECIMALES)
    if nouveau_stock < 0:
        raise ErreurMetier(
            409,
            "STOCK_INSUFFISANT",
            f"Il ne reste que {produit.stock_actuel:g} {produit.unite.value} de « {produit.nom} » : "
            f"impossible d'en retirer {abs(variation):g}.",
            {"produit_id": produit.id, "disponible": produit.stock_actuel, "demande": abs(variation)},
        )

    mouvement = Mouvement(
        produit_id=produit.id,
        type=type_,
        quantite=round(variation, DECIMALES),
        motif=motif,
        inventaire_id=inventaire_id,
    )
    produit.stock_actuel = nouveau_stock
    produit.maj_le = maintenant()
    session.add(mouvement)
    session.add(produit)
    return mouvement
