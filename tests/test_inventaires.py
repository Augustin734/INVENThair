import pytest

API = "/api/v1/inventaires"
PRODUITS = "/api/v1/produits"
MOUVEMENTS = "/api/v1/mouvements"


def _produit(client, nom, stock, unite="ml"):
    corps = {"nom": nom, "categorie_id": 1, "unite": unite, "seuil_alerte": 1, "qte_reappro": 1, "stock_initial": stock}
    reponse = client.post(PRODUITS, json=corps)
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def _stock(client, produit_id):
    return client.get(f"{PRODUITS}/{produit_id}").json()["stock_actuel"]


def _ouvrir(client):
    reponse = client.post(API)
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def _ligne(inventaire, nom):
    return next(l for l in inventaire["lignes"] if l["produit_nom"] == nom)


def _saisir(client, inventaire, nom, qte):
    reponse = client.patch(f"{API}/{inventaire['id']}/lignes/{_ligne(inventaire, nom)['id']}", json={"qte_comptee": qte})
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


@pytest.fixture
def stock(client):
    """Gel 35 ml, Capsules 60 pièces, Limes 12 pièces, et un produit archivé."""
    produits = {
        "Gel builder clair": _produit(client, "Gel builder clair", 35),
        "Capsules amande T4": _produit(client, "Capsules amande T4", 60, "piece"),
        "Limes 180/240": _produit(client, "Limes 180/240", 12, "piece"),
    }
    archive = _produit(client, "Strass AB 2 mm", 240, "piece")
    client.post(f"{PRODUITS}/{archive['id']}/archiver")
    return produits


# ---------- Ouverture (US8) ----------

def test_ouvrir_un_brouillon_avec_les_produits_actifs(client, stock):
    inventaire = _ouvrir(client)
    assert inventaire["statut"] == "brouillon" and inventaire["valide_le"] is None
    assert [l["produit_nom"] for l in inventaire["lignes"]] == ["Capsules amande T4", "Gel builder clair", "Limes 180/240"]
    gel = _ligne(inventaire, "Gel builder clair")
    assert (gel["qte_theorique"], gel["qte_comptee"], gel["ecart"], gel["unite"]) == (35, None, None, "ml")
    assert (inventaire["nb_lignes"], inventaire["nb_comptees"], inventaire["nb_ecarts"]) == (3, 0, 0)


def test_ouvrir_avec_commentaire(client):
    assert client.post(API, json={"commentaire": "Avant les fêtes"}).json()["commentaire"] == "Avant les fêtes"


def test_un_seul_brouillon_a_la_fois(client, stock):
    premier = _ouvrir(client)
    reponse = client.post(API)
    assert reponse.status_code == 409
    erreur = reponse.json()["erreur"]
    assert erreur["code"] == "INVENTAIRE_EN_COURS"
    assert erreur["details"] == {"inventaire_id": premier["id"]}


def test_lister_du_plus_recent_au_plus_ancien(client, stock):
    premier = _ouvrir(client)
    _saisir(client, premier, "Gel builder clair", 30)
    client.post(f"{API}/{premier['id']}/annuler")
    second = _ouvrir(client)
    liste = client.get(API).json()
    assert [i["id"] for i in liste] == [second["id"], premier["id"]]
    assert (liste[1]["statut"], liste[1]["nb_comptees"], liste[1]["nb_ecarts"]) == ("annule", 1, 1)
    assert "lignes" not in liste[0]


def test_detail(client, stock):
    inventaire = _ouvrir(client)
    reponse = client.get(f"{API}/{inventaire['id']}")
    assert reponse.status_code == 200
    assert reponse.json()["nb_lignes"] == 3


def test_detail_inconnu(client):
    reponse = client.get(f"{API}/999")
    assert reponse.status_code == 404
    assert reponse.json()["erreur"]["code"] == "INTROUVABLE"


# ---------- Comptage (US9) ----------

def test_saisir_un_comptage(client, stock):
    inventaire = _ouvrir(client)
    ligne = _saisir(client, inventaire, "Gel builder clair", 30)
    assert (ligne["qte_comptee"], ligne["ecart"]) == (30, -5)
    assert ligne["compte_le"] is not None
    assert client.get(f"{API}/{inventaire['id']}").json()["nb_comptees"] == 1
    assert _stock(client, stock["Gel builder clair"]["id"]) == 35  # rien ne bouge avant validation


def test_theorique_suit_le_stock_au_moment_du_comptage(client, stock):
    inventaire = _ouvrir(client)
    gel = stock["Gel builder clair"]["id"]
    client.post(MOUVEMENTS, json={"produit_id": gel, "type": "sortie", "quantite": 15})
    ligne = _saisir(client, inventaire, "Gel builder clair", 20)
    assert (ligne["qte_theorique"], ligne["ecart"]) == (20, 0)


def test_effacer_un_comptage(client, stock):
    inventaire = _ouvrir(client)
    _saisir(client, inventaire, "Gel builder clair", 30)
    ligne = _saisir(client, inventaire, "Gel builder clair", None)
    assert (ligne["qte_comptee"], ligne["ecart"], ligne["compte_le"]) == (None, None, None)


@pytest.mark.parametrize("corps", [{"qte_comptee": -1}, {}, {"qte_comptee": "trente"}, {"qte_comptee": 3, "ecart": 0}])
def test_saisie_invalide(client, stock, corps):
    inventaire = _ouvrir(client)
    ligne_id = _ligne(inventaire, "Gel builder clair")["id"]
    reponse = client.patch(f"{API}/{inventaire['id']}/lignes/{ligne_id}", json=corps)
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["code"] == "VALIDATION"


def test_saisir_ligne_inconnue(client, stock):
    inventaire = _ouvrir(client)
    assert client.patch(f"{API}/{inventaire['id']}/lignes/999", json={"qte_comptee": 1}).status_code == 404
    assert client.patch(f"{API}/999/lignes/1", json={"qte_comptee": 1}).status_code == 404


def test_saisir_ligne_d_un_autre_inventaire(client, stock):
    ancien = _ouvrir(client)
    client.post(f"{API}/{ancien['id']}/annuler")
    nouveau = _ouvrir(client)
    ligne_ancienne = _ligne(ancien, "Gel builder clair")["id"]
    assert client.patch(f"{API}/{nouveau['id']}/lignes/{ligne_ancienne}", json={"qte_comptee": 1}).status_code == 404


def test_archiver_un_produit_le_retire_du_brouillon(client, stock):
    inventaire = _ouvrir(client)
    client.post(f"{PRODUITS}/{stock['Limes 180/240']['id']}/archiver")
    detail = client.get(f"{API}/{inventaire['id']}").json()
    assert [l["produit_nom"] for l in detail["lignes"]] == ["Capsules amande T4", "Gel builder clair"]


# ---------- Validation (US10) ----------

def test_valider_cree_les_ajustements(client, stock):
    inventaire = _ouvrir(client)
    _saisir(client, inventaire, "Gel builder clair", 30)
    _saisir(client, inventaire, "Capsules amande T4", 72)
    _saisir(client, inventaire, "Limes 180/240", 12)

    reponse = client.post(f"{API}/{inventaire['id']}/valider", json={"garder_theorique_si_vide": False})
    assert reponse.status_code == 200
    valide = reponse.json()
    assert valide["statut"] == "valide" and valide["valide_le"] is not None
    assert valide["nb_ecarts"] == 2

    assert _stock(client, stock["Gel builder clair"]["id"]) == 30
    assert _stock(client, stock["Capsules amande T4"]["id"]) == 72
    historique = client.get(f"{PRODUITS}/{stock['Gel builder clair']['id']}/mouvements").json()
    assert (historique[0]["type"], historique[0]["quantite"], historique[0]["motif"], historique[0]["inventaire_id"]) == (
        "ajustement", -5, f"Inventaire N°{inventaire['id']}", inventaire["id"],
    )
    limes = client.get(f"{PRODUITS}/{stock['Limes 180/240']['id']}/mouvements").json()
    assert len(limes) == 1  # pas d'ajustement sans écart


def test_valider_sans_corps(client, stock):
    inventaire = _ouvrir(client)
    for nom in ("Gel builder clair", "Capsules amande T4", "Limes 180/240"):
        _saisir(client, inventaire, nom, 1)
    assert client.post(f"{API}/{inventaire['id']}/valider").status_code == 200


def test_lignes_non_comptees_refusees(client, stock):
    inventaire = _ouvrir(client)
    _saisir(client, inventaire, "Gel builder clair", 30)
    reponse = client.post(f"{API}/{inventaire['id']}/valider", json={"garder_theorique_si_vide": False})
    assert reponse.status_code == 409
    erreur = reponse.json()["erreur"]
    assert erreur["code"] == "LIGNES_NON_COMPTEES"
    assert erreur["details"] == {"nb_non_comptees": 2, "produits": ["Capsules amande T4", "Limes 180/240"]}
    assert client.get(f"{API}/{inventaire['id']}").json()["statut"] == "brouillon"
    assert _stock(client, stock["Gel builder clair"]["id"]) == 35


def test_garder_la_theorique_pour_les_non_comptees(client, stock):
    inventaire = _ouvrir(client)
    _saisir(client, inventaire, "Gel builder clair", 30)
    reponse = client.post(f"{API}/{inventaire['id']}/valider", json={"garder_theorique_si_vide": True})
    assert reponse.status_code == 200
    assert _stock(client, stock["Gel builder clair"]["id"]) == 30
    assert _stock(client, stock["Capsules amande T4"]["id"]) == 60
    assert len(client.get(f"{PRODUITS}/{stock['Capsules amande T4']['id']}/mouvements").json()) == 1


def test_mouvement_apres_comptage_conserve(client, stock):
    inventaire = _ouvrir(client)
    gel = stock["Gel builder clair"]["id"]
    _saisir(client, inventaire, "Gel builder clair", 30)  # écart −5
    client.post(MOUVEMENTS, json={"produit_id": gel, "type": "sortie", "quantite": 10})  # 35 → 25
    client.post(f"{API}/{inventaire['id']}/valider", json={"garder_theorique_si_vide": True})
    assert _stock(client, gel) == 20


def test_ajustement_negatif_refuse_sans_rien_ecrire(client, stock):
    inventaire = _ouvrir(client)
    limes, gel = stock["Limes 180/240"]["id"], stock["Gel builder clair"]["id"]
    _saisir(client, inventaire, "Gel builder clair", 30)  # écart −5, possible
    _saisir(client, inventaire, "Limes 180/240", 5)  # écart −7
    client.post(MOUVEMENTS, json={"produit_id": limes, "type": "sortie", "quantite": 10})  # 12 → 2

    reponse = client.post(f"{API}/{inventaire['id']}/valider", json={"garder_theorique_si_vide": True})
    assert reponse.status_code == 409
    erreur = reponse.json()["erreur"]
    assert erreur["code"] == "STOCK_INSUFFISANT"
    assert [l["produit_nom"] for l in erreur["details"]["lignes"]] == ["Limes 180/240"]
    assert (_stock(client, limes), _stock(client, gel)) == (2, 35)
    assert client.get(f"{API}/{inventaire['id']}").json()["statut"] == "brouillon"


def test_inventaire_valide_verrouille(client, stock):
    inventaire = _ouvrir(client)
    client.post(f"{API}/{inventaire['id']}/valider", json={"garder_theorique_si_vide": True})
    ligne_id = _ligne(inventaire, "Gel builder clair")["id"]
    for reponse in (
        client.post(f"{API}/{inventaire['id']}/valider", json={"garder_theorique_si_vide": True}),
        client.patch(f"{API}/{inventaire['id']}/lignes/{ligne_id}", json={"qte_comptee": 1}),
        client.post(f"{API}/{inventaire['id']}/annuler"),
    ):
        assert reponse.status_code == 409
        assert reponse.json()["erreur"]["code"] == "INVENTAIRE_VERROUILLE"


def test_valider_inconnu(client):
    assert client.post(f"{API}/999/valider").status_code == 404


def test_nouveau_brouillon_apres_validation(client, stock):
    inventaire = _ouvrir(client)
    client.post(f"{API}/{inventaire['id']}/valider", json={"garder_theorique_si_vide": True})
    assert client.post(API).status_code == 201


# ---------- Annulation ----------

def test_annuler_un_brouillon(client, stock):
    inventaire = _ouvrir(client)
    _saisir(client, inventaire, "Gel builder clair", 30)
    reponse = client.post(f"{API}/{inventaire['id']}/annuler")
    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "annule"
    assert _stock(client, stock["Gel builder clair"]["id"]) == 35
    assert client.post(API).status_code == 201


def test_annuler_inconnu(client):
    assert client.post(f"{API}/999/annuler").status_code == 404
