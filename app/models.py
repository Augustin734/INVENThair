"""Tables de la V1 (docs/cadrage.md § 2)."""

from datetime import datetime
from enum import Enum

from pydantic import NaiveDatetime

from sqlalchemy import CheckConstraint, Column, Index, String, UniqueConstraint, text
from sqlmodel import Field, SQLModel


def maintenant() -> datetime:
    """Heure locale à la seconde : l'appli tourne sur un seul PC."""
    return datetime.now().replace(microsecond=0)


def _nom_unique() -> Column:
    # NOCASE : SQLite refuse « gels » si « Gels » existe (casse ASCII uniquement,
    # le contrôle complet avec accents est fait dans les services).
    return Column(String(collation="NOCASE"), unique=True, nullable=False)


class Unite(str, Enum):
    piece = "piece"
    ml = "ml"
    g = "g"
    flacon = "flacon"


class TypeMouvement(str, Enum):
    entree = "entree"
    sortie = "sortie"
    ajustement = "ajustement"


class StatutInventaire(str, Enum):
    brouillon = "brouillon"
    valide = "valide"
    annule = "annule"


class Categorie(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint("couleur_r BETWEEN 0 AND 255", name="ck_categorie_r"),
        CheckConstraint("couleur_g BETWEEN 0 AND 255", name="ck_categorie_g"),
        CheckConstraint("couleur_b BETWEEN 0 AND 255", name="ck_categorie_b"),
        CheckConstraint("couleur_a BETWEEN 0.2 AND 1", name="ck_categorie_a"),
    )

    id: int | None = Field(default=None, primary_key=True)
    nom: str = Field(sa_column=_nom_unique())
    couleur_r: int
    couleur_g: int
    couleur_b: int
    couleur_a: float = 1.0
    ordre: int = 0
    cree_le: NaiveDatetime = Field(default_factory=maintenant)


class Fournisseur(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nom: str = Field(sa_column=_nom_unique())
    email: str | None = None
    site_url: str | None = None
    notes: str | None = None
    cree_le: NaiveDatetime = Field(default_factory=maintenant)


class Produit(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nom: str
    reference: str | None = None
    categorie_id: int = Field(foreign_key="categorie.id", index=True)
    fournisseur_id: int | None = Field(default=None, foreign_key="fournisseur.id", index=True)
    unite: Unite
    stock_actuel: float = 0.0
    seuil_alerte: float
    qte_reappro: float
    prix_unitaire: float | None = None
    archive: bool = Field(default=False, index=True)
    archive_motif: str | None = None
    archive_le: NaiveDatetime | None = None
    cree_le: NaiveDatetime = Field(default_factory=maintenant)
    maj_le: NaiveDatetime = Field(default_factory=maintenant)


class Mouvement(SQLModel, table=True):
    """Jamais modifié ni supprimé : toute variation de stock en laisse un."""

    __table_args__ = (Index("ix_mouvement_produit_date", "produit_id", "cree_le"),)

    id: int | None = Field(default=None, primary_key=True)
    produit_id: int = Field(foreign_key="produit.id")
    type: TypeMouvement
    quantite: float
    motif: str | None = None
    inventaire_id: int | None = Field(default=None, foreign_key="inventaire.id")
    cree_le: NaiveDatetime = Field(default_factory=maintenant, index=True)


class Inventaire(SQLModel, table=True):
    __table_args__ = (
        # Un seul brouillon à la fois, garanti par la base elle-même.
        Index(
            "ux_inventaire_un_brouillon",
            "statut",
            unique=True,
            sqlite_where=text("statut = 'brouillon'"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    statut: StatutInventaire = StatutInventaire.brouillon
    commentaire: str | None = None
    cree_le: NaiveDatetime = Field(default_factory=maintenant)
    valide_le: NaiveDatetime | None = None


class LigneInventaire(SQLModel, table=True):
    __tablename__ = "ligne_inventaire"
    __table_args__ = (UniqueConstraint("inventaire_id", "produit_id", name="uq_ligne_produit"),)

    id: int | None = Field(default=None, primary_key=True)
    inventaire_id: int = Field(foreign_key="inventaire.id", index=True)
    produit_id: int = Field(foreign_key="produit.id")
    qte_theorique: float
    qte_comptee: float | None = None
    compte_le: NaiveDatetime | None = None

    @property
    def ecart(self) -> float | None:
        if self.qte_comptee is None:
            return None
        return self.qte_comptee - self.qte_theorique
