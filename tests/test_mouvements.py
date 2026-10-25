import pytest
from sqlmodel import Session, select

from app.models import Mouvement

API = "/api/v1/mouvements"
PRODUITS = "/api/v1/produits"


def _produit(client, nom="Gel builder clair", stock=35, unite="ml"):
    corps = {"nom": nom, "categorie_id": 1, "unite": unite, "seuil_alerte": 50, "qte_reappro": 100, "stock_initial": stock}
    reponse = client.post(PRODUITS, json=corps)
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def _stock(client, produit_id):
    return client.get(f"{PRODUITS}/{produit_id}").json()["stock_actuel"]


def _nb_mouvements(client):
    with Session(client.app.state.moteur) as s:
        return len(s.exec(select(Mouvement)).all())


# ---------- POST /mouvements (US5, US6) ----------

def test_reception(client):
    p = _produit(client)
    reponse = client.post(API, json={"produit_id": p["id"], "type": "entree", "quantite": 100, "motif": "Réception commande"})
    assert reponse.status_code == 201
    m = reponse.json()
    assert (m["type"], m["quantite"], m["motif"], m["produit_nom"], m["unite"]) == ("entree", 100, "Réception commande", "Gel builder clair", "ml")
    assert m["inventaire_id"] is None
    assert _stock(client, p["id"]) == 135


def test_sortie_signee_negativement(client):
    p = _produit(client)
    m = client.post(API, json={"produit_id": p["id"], "type": "sortie", "quantite": 15, "motif": "Perte"}).json()
    assert m["quantite"] == -15
    assert _stock(client, p["id"]) == 20


def test_sortie_de_tout_le_stock(client):
    p = _produit(client)
    assert client.post(API, json={"produit_id": p["id"], "type": "sortie", "quantite": 35}).status_code == 201
    assert _stock(client, p["id"]) == 0


def test_sortie_refusee_si_stock_insuffisant(client):
    p = _produit(client)
    avant = _nb_mouvements(client)
    reponse = client.post(API, json={"produit_id": p["id"], "type": "sortie", "quantite": 50})
    assert reponse.status_code == 409
    erreur = reponse.json()["erreur"]
    assert erreur["code"] == "STOCK_INSUFFISANT"
    assert erreur["message"] == "Il ne reste que 35 ml de « Gel builder clair » : impossible d'en retirer 50."
    assert _stock(client, p["id"]) == 35
    assert _nb_mouvements(client) == avant


def test_produit_archive_refuse(client):
    p = _produit(client)
    client.post(f"{PRODUITS}/{p['id']}/archiver")
    reponse = client.post(API, json={"produit_id": p["id"], "type": "entree", "quantite": 5})
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "PRODUIT_ARCHIVE"


@pytest.mark.parametrize(
    "modif, champ",
    [({"type": "ajustement"}, "type"), ({"quantite": 0}, "quantite"), ({"quantite": -3}, "quantite"), ({"produit_id": 999}, "produit_id"), ({"stock_actuel": 3}, "stock_actuel")],
)
def test_mouvement_invalide(client, modif, champ):
    p = _produit(client)
    corps = {"produit_id": p["id"], "type": "entree", "quantite": 5, **modif}
    reponse = client.post(API, json=corps)
    assert reponse.status_code == 422
    assert champ in reponse.json()["erreur"]["details"]
    assert _stock(client, p["id"]) == 35


def test_motif_vide_devient_null(client):
    p = _produit(client)
    assert client.post(API, json={"produit_id": p["id"], "type": "entree", "quantite": 1, "motif": "  "}).json()["motif"] is None


# ---------- GET /produits/{id}/mouvements (US7) ----------

def test_historique_du_plus_recent_au_plus_ancien(client):
    p = _produit(client, stock=60)
    client.post(API, json={"produit_id": p["id"], "type": "sortie", "quantite": 40, "motif": "Utilisation"})
    client.post(API, json={"produit_id": p["id"], "type": "entree", "quantite": 100, "motif": "Réception commande"})
    autre = _produit(client, nom="Autre")
    client.post(API, json={"produit_id": autre["id"], "type": "entree", "quantite": 1})

    reponse = client.get(f"{PRODUITS}/{p['id']}/mouvements")
    assert reponse.status_code == 200
    assert [(m["quantite"], m["motif"]) for m in reponse.json()] == [(100, "Réception commande"), (-40, "Utilisation"), (60, "Stock initial")]


def test_historique_produit_archive_reste_consultable(client):
    p = _produit(client)
    client.post(f"{PRODUITS}/{p['id']}/archiver")
    assert len(client.get(f"{PRODUITS}/{p['id']}/mouvements").json()) == 1


def test_historique_produit_inconnu(client):
    reponse = client.get(f"{PRODUITS}/999/mouvements")
    assert reponse.status_code == 404
    assert reponse.json()["erreur"]["code"] == "INTROUVABLE"


# ---------- GET /mouvements (accueil) ----------

def test_derniers_mouvements_tous_produits(client):
    for i in range(7):
        _produit(client, nom=f"Produit {i}", stock=i + 1)
    reponse = client.get(API)
    assert reponse.status_code == 200
    assert [m["produit_nom"] for m in reponse.json()] == [f"Produit {i}" for i in (6, 5, 4, 3, 2)]
    assert [m["produit_nom"] for m in client.get(API, params={"limite": 2}).json()] == ["Produit 6", "Produit 5"]


@pytest.mark.parametrize("limite", [0, 101, "beaucoup"])
def test_derniers_limite_invalide(client, limite):
    reponse = client.get(API, params={"limite": limite})
    assert reponse.status_code == 422
    assert "limite" in reponse.json()["erreur"]["details"]
