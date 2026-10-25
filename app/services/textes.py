import unicodedata


def cle_unicite(nom: str) -> str:
    """Comparaison des noms uniques : insensible à la casse (« Gels » = « gels »)."""
    return nom.strip().casefold()


def cle_tri(texte: str) -> str:
    """Tri et recherche : insensibles à la casse et aux accents (« Écrin » proche de « ecrin »)."""
    decompose = unicodedata.normalize("NFKD", texte.casefold())
    return "".join(c for c in decompose if not unicodedata.combining(c))
