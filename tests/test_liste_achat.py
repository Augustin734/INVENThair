from datetime import date

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


# ---------- Exports (US13) ----------

EXPORT = "/api/v1/liste-achat/export"


def _liste(client):
    return client.get("/api/v1/liste-achat").json()


def test_export_csv(client, boutique):
    liste = _liste(client)
    liste["fournisseurs"][0]["lignes"][0]["quantite"] = 12.5  # retouchée par Maud
    reponse = client.post(EXPORT, params={"format": "csv"}, json=liste)
    assert reponse.status_code == 200
    assert reponse.headers["content-type"].startswith("text/csv")
    assert reponse.headers["content-disposition"] == f'attachment; filename="liste-achat-{date.today():%Y-%m-%d}.csv"'
    assert reponse.content.startswith("﻿".encode())
    lignes = reponse.content.decode("utf-8-sig").splitlines()
    assert lignes[0] == "Fournisseur;Produit;Unité;Stock actuel;Seuil d'alerte;Quantité à commander"
    assert lignes[1] == "Grossiste A;Gel builder clair;ml;35;50;12,5"
    assert lignes[-1] == "Sans fournisseur;Cotons;pièce;0;100;500"


def test_export_ignore_quantites_nulles(client, boutique):
    liste = _liste(client)
    for ligne in liste["fournisseurs"][1]["lignes"]:
        ligne["quantite"] = 0
    contenu = client.post(EXPORT, params={"format": "csv"}, json=liste).content.decode("utf-8-sig")
    assert "Grossiste B" not in contenu


def test_export_avec_produit_hors_alerte_ajoute(client, boutique):
    liste = _liste(client)
    liste["fournisseurs"][0]["lignes"].append(
        {"produit_id": 5, "nom": "Primer sans acide", "unite": "piece", "stock_actuel": 6, "seuil_alerte": 2, "quantite": 3}
    )
    assert "Primer sans acide" in client.post(EXPORT, params={"format": "csv"}, json=liste).content.decode("utf-8-sig")


def test_export_pdf(client, boutique):
    reponse = client.post(EXPORT, params={"format": "pdf"}, json=_liste(client))
    assert reponse.status_code == 200
    assert reponse.headers["content-type"] == "application/pdf"
    assert reponse.headers["content-disposition"].endswith('.pdf"')
    assert reponse.content.startswith(b"%PDF-") and reponse.content.rstrip().endswith(b"%%EOF")


def test_export_pdf_liste_vide(client):
    reponse = client.post(EXPORT, params={"format": "pdf"}, json={"fournisseurs": []})
    assert reponse.status_code == 200
    assert reponse.content.startswith(b"%PDF-")


@pytest.mark.parametrize("params", [{"format": "xlsx"}, {}])
def test_export_format_invalide(client, params):
    reponse = client.post(EXPORT, params=params, json={"fournisseurs": []})
    assert reponse.status_code == 422
    assert "format" in reponse.json()["erreur"]["details"]


def test_export_corps_invalide(client, boutique):
    liste = _liste(client)
    liste["fournisseurs"][0]["lignes"][0]["quantite"] = -1
    reponse = client.post(EXPORT, params={"format": "csv"}, json=liste)
    assert reponse.status_code == 422
    assert "fournisseurs.0.lignes.0.quantite" in reponse.json()["erreur"]["details"]


@pytest.mark.parametrize("route", ["/api/v1/alertes", "/api/v1/liste-achat"])
def test_lectures_seulement(client, route):
    assert client.delete(route).json()["erreur"]["code"] == "METHODE_NON_AUTORISEE"
