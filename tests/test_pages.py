"""Pages HTML et fichiers statiques. Le comportement des écrans est vérifié dans un navigateur (voir la PR)."""

import pytest

PAGES = [("/", "Accueil"), ("/produits", "Produits"), ("/produits?onglet=archives", "Produits"), ("/produits/1", "Fiche produit")]


@pytest.mark.parametrize("url, titre", PAGES)
def test_page_servie(client, url, titre):
    reponse = client.get(url)
    assert reponse.status_code == 200
    assert reponse.headers["content-type"].startswith("text/html")
    assert f"<title>{titre} · INVENThair</title>" in reponse.text
    assert 'aria-current="page"' in reponse.text
    assert "/static/style.css?v=" in reponse.text


@pytest.mark.parametrize(
    "fichier, type_attendu",
    [
        ("/static/style.css", "text/css"),
        ("/static/js/commun.js", "javascript"),
        ("/static/js/accueil.js", "javascript"),
        ("/static/js/produits.js", "javascript"),
        ("/static/js/fiche_produit.js", "javascript"),
        ("/static/js/selecteur_couleur.js", "javascript"),
        ("/static/js/fenetres/produit.js", "javascript"),
        ("/static/js/fenetres/mouvement.js", "javascript"),
        ("/static/js/fenetres/archiver.js", "javascript"),
        ("/static/js/fenetres/categories.js", "javascript"),
        ("/static/js/fenetres/fournisseurs.js", "javascript"),
        ("/static/fonts/lilita-one-400.woff2", "font/woff2"),
        ("/static/fonts/nunito-variable.woff2", "font/woff2"),
    ],
)
def test_fichiers_statiques(client, fichier, type_attendu):
    reponse = client.get(fichier)
    assert reponse.status_code == 200
    assert type_attendu in reponse.headers["content-type"]


def test_aucune_ressource_externe(client):
    """L'appli doit marcher hors ligne : ni Google Fonts ni CDN."""
    for url, _ in PAGES:
        html = client.get(url).text
        assert "googleapis" not in html and "https://" not in html


def test_page_inconnue(client):
    assert client.get("/nexiste-pas").status_code == 404


def test_fiche_produit_identifiant_invalide(client):
    reponse = client.get("/produits/abc")
    assert reponse.status_code == 422
