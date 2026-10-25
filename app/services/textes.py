import unicodedata


def cle_unicite(nom: str) -> str:
    """Comparaison des noms uniques : insensible à la casse (« Gels » = « gels »)."""
    return nom.strip().casefold()


def cle_tri(texte: str) -> str:
    """Tri et recherche : insensibles à la casse et aux accents (« Écrin » proche de « ecrin »)."""
    decompose = unicodedata.normalize("NFKD", texte.casefold())
    return "".join(c for c in decompose if not unicodedata.combining(c))


JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
UNITES = {"piece": ("pièce", "pièces"), "flacon": ("flacon", "flacons"), "ml": ("ml", "ml"), "g": ("g", "g")}


def nombre_fr(valeur: float) -> str:
    """35.0 → « 35 », 0.5 → « 0,5 » (sans séparateur de milliers, lisible par un tableur)."""
    texte = f"{round(valeur, 3):f}".rstrip("0").rstrip(".")
    return texte.replace(".", ",") if texte not in ("", "-0") else "0"


def unite_fr(unite: str, quantite: float) -> str:
    singulier, pluriel = UNITES[unite]
    return pluriel if abs(quantite) >= 2 else singulier


def quantite_fr(quantite: float, unite: str) -> str:
    return f"{nombre_fr(quantite)} {unite_fr(unite, quantite)}"


def date_fr(moment) -> str:
    """« samedi 24 octobre 2026 »."""
    return f"{JOURS[moment.weekday()]} {moment.day} {MOIS[moment.month - 1]} {moment.year}"
