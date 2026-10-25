import pytest

PRODUITS = "/api/v1/produits"


def _fournisseur(client, nom):
    return client.post("/api/v1/fournisseurs", json={"nom": nom}).json()["id"]


def _produit(client, nom, stock, seuil=10, reappro=50, fournisseur_id=None, unite="piece"):
    corps = {"nom": nom, "categorie_id": 1, "unite": unite, "seuil_alerte": seuil, "qte_reappro": reappro, "stock_initial": stock, "fournisseur_id": fournisseur_id}
    reponse = client.post(PRODUITS, json=corps)
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


@pytest.fixture
def boutique(client):
    a = _fournisseur(client, "Grossiste A")
    b = _fournisseur(client, "Grossiste B")
    _produit(client, "Limes 180/240", 12, seuil=20, fournisseur_id=a)
    _produit(client, "Gel builder clair", 35, seuil=50, reappro=100, fournisseur_id=a, unite="ml")
    _produit(client, "Top coat brillant", 1, seuil=3, reappro=5, fournisseur_id=b, unite="flacon")
    _produit(client, "Cotons", 0, seuil=100, reappro=500)
    _produit(client, "Primer sans acide", 6, seuil=2, fournisseur_id=a)  # en forme
    archive = _produit(client, "Strass", 0, fournisseur_id=b)
    client.post(f"{PRODUITS}/{archive['id']}/archiver")
    return {"a": a, "b": b}


def test_alertes(client, boutique):
    reponse = client.get("/api/v1/alertes")
    assert reponse.status_code == 200
    assert [p["nom"] for p in reponse.json()] == ["Cotons", "Gel builder clair", "Limes 180/240", "Top coat brillant"]
    assert all(p["en_alerte"] and p["statut"] == "alerte" for p in reponse.json())


def test_alertes_vide(client):
    assert client.get("/api/v1/alertes").json() == []


def test_liste_achat_groupee_par_fournisseur(client, boutique):
    reponse = client.get("/api/v1/liste-achat")
    assert reponse.status_code == 200
    liste = reponse.json()
    assert liste["genere_le"] is not None
    assert [(g["fournisseur_id"], g["nom"]) for g in liste["fournisseurs"]] == [
        (boutique["a"], "Grossiste A"), (boutique["b"], "Grossiste B"), (None, "Sans fournisseur"),
    ]
    assert liste["fournisseurs"][0]["lignes"] == [
        {"produit_id": 2, "nom": "Gel builder clair", "unite": "ml", "stock_actuel": 35, "seuil_alerte": 50, "quantite": 100},
        {"produit_id": 1, "nom": "Limes 180/240", "unite": "piece", "stock_actuel": 12, "seuil_alerte": 20, "quantite": 50},
    ]


def test_liste_achat_vide(client):
    assert client.get("/api/v1/liste-achat").json()["fournisseurs"] == []
