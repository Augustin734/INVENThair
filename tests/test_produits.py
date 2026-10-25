import pytest
from sqlmodel import Session, select

from app.models import Inventaire, LigneInventaire, Mouvement, StatutInventaire

API = "/api/v1/produits"


def _corps(**autres):
    corps = {"nom": "Gel builder clair", "reference": "GB-50", "categorie_id": 1, "unite": "ml", "seuil_alerte": 50, "qte_reappro": 100}
    corps.update(autres)
    return corps


def _creer(client, **autres):
    reponse = client.post(API, json=_corps(**autres))
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


# ---------- Création (US1) ----------

def test_creer_avec_stock_initial(client):
    produit = _creer(client, stock_initial=35, prix_unitaire=0.24)
    assert produit["stock_actuel"] == 35
    assert produit["archive"] is False and produit["archive_le"] is None
    with Session(client.app.state.moteur) as s:
        mouvements = s.exec(select(Mouvement)).all()
    assert [(m.type.value, m.quantite, m.motif) for m in mouvements] == [("entree", 35, "Stock initial")]


def test_creer_sans_stock_ne_cree_pas_de_mouvement(client):
    assert _creer(client)["stock_actuel"] == 0
    with Session(client.app.state.moteur) as s:
        assert s.exec(select(Mouvement)).all() == []


@pytest.mark.parametrize("retire", ["nom", "categorie_id", "unite", "seuil_alerte", "qte_reappro"])
def test_champs_obligatoires(client, retire):
    corps = _corps()
    del corps[retire]
    reponse = client.post(API, json=corps)
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["details"][retire] == "Champ obligatoire."


@pytest.mark.parametrize(
    "modif, champ",
    [({"unite": "litre"}, "unite"), ({"seuil_alerte": -1}, "seuil_alerte"), ({"stock_initial": -5}, "stock_initial"), ({"categorie_id": 999}, "categorie_id"), ({"fournisseur_id": 999}, "fournisseur_id")],
)
def test_creation_invalide(client, modif, champ):
    reponse = client.post(API, json=_corps(**modif))
    assert reponse.status_code == 422
    assert champ in reponse.json()["erreur"]["details"]


# ---------- Liste (US2) ----------

def test_liste_triee_par_nom_sans_accents(client):
    for nom in ["Vernis", "étuis", "capsules", "Base coat"]:
        _creer(client, nom=nom)
    assert [p["nom"] for p in client.get(API).json()] == ["Base coat", "capsules", "étuis", "Vernis"]


def test_filtre_par_categorie(client):
    _creer(client, nom="Gel", categorie_id=1)
    _creer(client, nom="Vernis rouge", categorie_id=2)
    assert [p["nom"] for p in client.get(API, params={"categorie_id": 2}).json()] == ["Vernis rouge"]


@pytest.mark.parametrize("q, attendu", [("GEL", ["Gel builder clair"]), ("ecrin", ["Écrin à pinceaux"]), ("vp-ar", ["Vernis pailleté"]), ("   ", ["Écrin à pinceaux", "Gel builder clair", "Vernis pailleté"])])
def test_recherche_nom_et_reference(client, q, attendu):
    _creer(client, nom="Gel builder clair", reference="GB-50")
    _creer(client, nom="Écrin à pinceaux", reference=None)
    _creer(client, nom="Vernis pailleté", reference="VP-AR")
    assert sorted(p["nom"] for p in client.get(API, params={"q": q}).json()) == sorted(attendu)


def test_filtre_en_alerte(client):
    _creer(client, nom="Bas", stock_initial=10)
    _creer(client, nom="Haut", stock_initial=500)
    assert [p["nom"] for p in client.get(API, params={"en_alerte": True}).json()] == ["Bas"]
    assert [p["nom"] for p in client.get(API, params={"en_alerte": False}).json()] == ["Haut"]


def test_filtre_invalide(client):
    reponse = client.get(API, params={"categorie_id": "gels"})
    assert reponse.status_code == 422
    assert "categorie_id" in reponse.json()["erreur"]["details"]


@pytest.mark.parametrize(
    "stock, statut, alerte",
    [(0, "alerte", True), (50, "alerte", True), (51, "a_surveiller", False), (75, "a_surveiller", False), (76, "en_forme", False)],
)
def test_statut_calcule(client, stock, statut, alerte):
    produit = _creer(client, stock_initial=stock)
    assert (produit["statut"], produit["en_alerte"]) == (statut, alerte)


# ---------- Détail et modification (US3) ----------

def test_detail(client):
    produit = _creer(client)
    reponse = client.get(f"{API}/{produit['id']}")
    assert reponse.status_code == 200
    assert reponse.json()["nom"] == "Gel builder clair"


def test_detail_inconnu(client):
    reponse = client.get(f"{API}/999")
    assert reponse.status_code == 404
    assert reponse.json()["erreur"]["message"] == "Produit introuvable."


def test_modifier_categorie_et_effacer_reference(client):
    produit = _creer(client)
    reponse = client.patch(f"{API}/{produit['id']}", json={"categorie_id": 2, "reference": None, "seuil_alerte": 10})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert (corps["categorie_id"], corps["reference"], corps["seuil_alerte"]) == (2, None, 10)


def test_stock_non_modifiable(client):
    produit = _creer(client, stock_initial=35)
    reponse = client.patch(f"{API}/{produit['id']}", json={"stock_actuel": 999})
    assert reponse.status_code == 422
    assert "stock_actuel" in reponse.json()["erreur"]["details"]
    assert client.get(f"{API}/{produit['id']}").json()["stock_actuel"] == 35


@pytest.mark.parametrize("corps", [{"nom": None}, {"categorie_id": 999}, {"unite": None}])
def test_modification_invalide(client, corps):
    produit = _creer(client)
    assert client.patch(f"{API}/{produit['id']}", json=corps).status_code == 422


def test_modifier_inconnu(client):
    assert client.patch(f"{API}/999", json={"nom": "X"}).status_code == 404


# ---------- Archivage (US4) ----------

def test_archiver_puis_desarchiver(client):
    produit = _creer(client, nom="Strass AB 2 mm", stock_initial=10)
    reponse = client.post(f"{API}/{produit['id']}/archiver", json={"motif": "Les clientes n'accrochent pas"})
    assert reponse.status_code == 200
    archive = reponse.json()
    assert archive["archive"] is True and archive["archive_le"] is not None
    assert archive["archive_motif"] == "Les clientes n'accrochent pas"
    assert archive["en_alerte"] is False

    assert client.get(API).json() == []
    assert client.get(API, params={"en_alerte": True}).json() == []
    assert [p["nom"] for p in client.get(API, params={"archive": True}).json()] == ["Strass AB 2 mm"]

    reponse = client.post(f"{API}/{produit['id']}/desarchiver")
    assert reponse.status_code == 200
    assert (reponse.json()["archive"], reponse.json()["archive_motif"], reponse.json()["archive_le"]) == (False, None, None)
    assert [p["nom"] for p in client.get(API).json()] == ["Strass AB 2 mm"]


def test_archiver_sans_corps(client):
    produit = _creer(client)
    reponse = client.post(f"{API}/{produit['id']}/archiver")
    assert reponse.status_code == 200
    assert reponse.json()["archive_motif"] is None


def test_archiver_retire_du_brouillon_seulement(client):
    produit = _creer(client)
    with Session(client.app.state.moteur) as s:
        ancien = Inventaire(statut=StatutInventaire.valide)
        brouillon = Inventaire(statut=StatutInventaire.brouillon)
        s.add_all([ancien, brouillon])
        s.flush()
        s.add_all([
            LigneInventaire(inventaire_id=ancien.id, produit_id=produit["id"], qte_theorique=0, qte_comptee=0),
            LigneInventaire(inventaire_id=brouillon.id, produit_id=produit["id"], qte_theorique=0),
        ])
        s.commit()
        ids = (ancien.id, brouillon.id)

    client.post(f"{API}/{produit['id']}/archiver")

    with Session(client.app.state.moteur) as s:
        restantes = [l.inventaire_id for l in s.exec(select(LigneInventaire))]
    assert restantes == [ids[0]]


@pytest.mark.parametrize("action", ["archiver", "desarchiver"])
def test_archivage_produit_inconnu(client, action):
    assert client.post(f"{API}/999/{action}").status_code == 404


def test_motif_trop_long(client):
    produit = _creer(client)
    assert client.post(f"{API}/{produit['id']}/archiver", json={"motif": "x" * 201}).status_code == 422
