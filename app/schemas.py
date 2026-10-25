"""Objets échangés par l'API (docs/cadrage.md § 4)."""

import re
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, NaiveDatetime, StringConstraints, field_validator, model_validator

from app.models import Unite

Nom = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
TexteCourt = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
TexteLong = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Quantite = Annotated[float, Field(ge=0)]

MOTIF_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Entree(BaseModel):
    """Base des corps de requête : champ inconnu = erreur 422 (ex. `stock_actuel` sur un PATCH)."""

    model_config = ConfigDict(extra="forbid")


class Modification(Entree):
    """Base des PATCH : seuls les champs envoyés sont modifiés ; `null` efface un champ facultatif."""

    NON_NULS: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def _refuser_null_sur_obligatoires(self):
        for champ in self.NON_NULS:
            if champ in self.model_fields_set and getattr(self, champ) is None:
                raise ValueError(f"« {champ} » ne peut pas être vide.")
        return self

    def changements(self) -> dict:
        return self.model_dump(exclude_unset=True)


def _vide_vers_none(valeur: str | None) -> str | None:
    return valeur or None


# ---------- Erreurs (documentation OpenAPI) ----------

class DetailErreur(BaseModel):
    code: str
    message: str
    details: dict = {}


class ReponseErreur(BaseModel):
    erreur: DetailErreur


_DESCRIPTIONS_ERREURS = {
    404: "INTROUVABLE",
    409: "Conflit métier (voir le code)",
    422: "VALIDATION, détails par champ",
    502: "ENVOI_MAIL_ECHOUE",
}


def erreurs(*statuts: int) -> dict:
    """Réponses d'erreur à documenter sur une route ; 422 est toujours possible."""
    return {s: {"model": ReponseErreur, "description": _DESCRIPTIONS_ERREURS[s]} for s in sorted({*statuts, 422})}


# ---------- Santé ----------

class Sante(BaseModel):
    status: Literal["ok"] = "ok"


# ---------- Catégories ----------

class Couleur(BaseModel):
    r: int = Field(ge=0, le=255)
    g: int = Field(ge=0, le=255)
    b: int = Field(ge=0, le=255)
    a: float = Field(default=1.0, ge=0.2, le=1.0)


COULEUR_PAR_DEFAUT = Couleur(r=176, g=16, b=80, a=1.0)  # pivoine


class CategorieCreation(Entree):
    nom: Nom
    couleur: Couleur = COULEUR_PAR_DEFAUT


class CategorieModification(Modification):
    NON_NULS = ("nom", "couleur", "ordre")

    nom: Nom | None = None
    couleur: Couleur | None = None
    ordre: int | None = Field(default=None, ge=0)


class Reordonnancement(Entree):
    ids: list[int] = Field(min_length=1)


class Categorie(BaseModel):
    id: int
    nom: str
    couleur: Couleur
    ordre: int
    nb_produits: int
    cree_le: NaiveDatetime


# ---------- Fournisseurs ----------

class _ChampsFournisseur(Entree):
    @field_validator("email", "site_url", "notes", check_fields=False)
    @classmethod
    def _vide(cls, valeur):
        return _vide_vers_none(valeur)

    @field_validator("email", check_fields=False)
    @classmethod
    def _email(cls, valeur):
        if valeur is not None and not MOTIF_EMAIL.match(valeur):
            raise ValueError("Adresse mail invalide.")
        return valeur


class FournisseurCreation(_ChampsFournisseur):
    nom: Nom
    email: TexteCourt | None = None
    site_url: TexteCourt | None = None
    notes: TexteLong | None = None


class FournisseurModification(_ChampsFournisseur, Modification):
    NON_NULS = ("nom",)

    nom: Nom | None = None
    email: TexteCourt | None = None
    site_url: TexteCourt | None = None
    notes: TexteLong | None = None


class Fournisseur(BaseModel):
    id: int
    nom: str
    email: str | None
    site_url: str | None
    notes: str | None
    nb_produits: int
    cree_le: NaiveDatetime


# ---------- Produits ----------

StatutProduit = Literal["en_forme", "a_surveiller", "alerte"]


class _ChampsProduit(Entree):
    @field_validator("reference", check_fields=False)
    @classmethod
    def _vide(cls, valeur):
        return _vide_vers_none(valeur)


class ProduitCreation(_ChampsProduit):
    nom: Nom
    reference: TexteCourt | None = None
    categorie_id: int
    fournisseur_id: int | None = None
    unite: Unite
    seuil_alerte: Quantite
    qte_reappro: Quantite
    prix_unitaire: Quantite | None = None
    stock_initial: Quantite | None = None


class ProduitModification(_ChampsProduit, Modification):
    NON_NULS = ("nom", "categorie_id", "unite", "seuil_alerte", "qte_reappro")

    nom: Nom | None = None
    reference: TexteCourt | None = None
    categorie_id: int | None = None
    fournisseur_id: int | None = None
    unite: Unite | None = None
    seuil_alerte: Quantite | None = None
    qte_reappro: Quantite | None = None
    prix_unitaire: Quantite | None = None


class Archivage(Entree):
    motif: TexteCourt | None = None

    @field_validator("motif")
    @classmethod
    def _vide(cls, valeur):
        return _vide_vers_none(valeur)


class Produit(BaseModel):
    id: int
    nom: str
    reference: str | None
    categorie_id: int
    fournisseur_id: int | None
    unite: Unite
    stock_actuel: float
    seuil_alerte: float
    qte_reappro: float
    prix_unitaire: float | None
    archive: bool
    archive_motif: str | None
    archive_le: NaiveDatetime | None
    en_alerte: bool
    statut: StatutProduit
    cree_le: NaiveDatetime
    maj_le: NaiveDatetime
