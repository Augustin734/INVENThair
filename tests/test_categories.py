import pytest
from sqlmodel import Session

from app.models import Produit, Unite

API = "/api/v1/categories"


def _ajouter_produit(client, categorie_id, archive=False):
    """Insère un produit directement en base (les routes produits ont leurs propres tests)."""
    with Session(client.app.state.moteur) as s:
        p = Produit(nom="Essai", categorie_id=categorie_id, unite=Unite.piece, seuil_alerte=1, qte_reappro=1, archive=archive)
        s.add(p)
        s.commit()
        return p.id


def _ids(client):
    return {c["nom"]: c["id"] for c in client.get(API).json()}


def test_lister_categories_de_depart(client):
    reponse = client.get(API)
    assert reponse.status_code == 200
    gels = reponse.json()[0]
    assert gels["nom"] == "Gels"
    assert gels["couleur"] == {"r": 176, "g": 16, "b": 80, "a": 1.0}
    assert gels["ordre"] == 1 and gels["nb_produits"] == 0


def test_creer_categorie_en_dernier(client):
    reponse = client.post(API, json={"nom": "  Strass  ", "couleur": {"r": 196, "g": 121, "b": 20, "a": 0.85}})
    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["nom"] == "Strass"
    assert corps["ordre"] == 5
    assert corps["couleur"]["a"] == 0.85


def test_creer_sans_couleur_prend_pivoine(client):
    assert client.post(API, json={"nom": "Déco"}).json()["couleur"] == {"r": 176, "g": 16, "b": 80, "a": 1.0}


@pytest.mark.parametrize("nom", ["Gels", "gels", "GELS ", "vernis"])
def test_nom_en_double_refuse(client, nom):
    reponse = client.post(API, json={"nom": nom})
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "NOM_DEJA_UTILISE"


@pytest.mark.parametrize(
    "corps, champ",
    [({"nom": ""}, "nom"), ({"nom": "X", "couleur": {"r": 300, "g": 0, "b": 0}}, "couleur.r"), ({"nom": "X", "couleur": {"r": 0, "g": 0, "b": 0, "a": 0.1}}, "couleur.a")],
)
def test_creation_invalide(client, corps, champ):
    reponse = client.post(API, json=corps)
    assert reponse.status_code == 422
    assert champ in reponse.json()["erreur"]["details"]


def test_renommer_et_recolorer(client):
    id_gels = _ids(client)["Gels"]
    reponse = client.patch(f"{API}/{id_gels}", json={"nom": "Gels UV", "couleur": {"r": 0, "g": 0, "b": 0, "a": 0.5}})
    assert reponse.status_code == 200
    assert reponse.json()["nom"] == "Gels UV"
    assert reponse.json()["couleur"]["a"] == 0.5


def test_renommer_meme_nom_autre_casse_autorise(client):
    id_gels = _ids(client)["Gels"]
    assert client.patch(f"{API}/{id_gels}", json={"nom": "GELS"}).status_code == 200


def test_renommer_vers_nom_existant_refuse(client):
    id_gels = _ids(client)["Gels"]
    assert client.patch(f"{API}/{id_gels}", json={"nom": "Vernis"}).json()["erreur"]["code"] == "NOM_DEJA_UTILISE"


def test_modifier_nom_null_refuse(client):
    id_gels = _ids(client)["Gels"]
    reponse = client.patch(f"{API}/{id_gels}", json={"nom": None})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["details"] == {"nom": "Ne peut pas être vide."}


def test_modifier_inconnue(client):
    reponse = client.patch(f"{API}/999", json={"nom": "X"})
    assert reponse.status_code == 404
    assert reponse.json()["erreur"]["code"] == "INTROUVABLE"


def test_reordonner(client):
    ids = _ids(client)
    nouvel_ordre = [ids["Consommables"], ids["Gels"], ids["Capsules"], ids["Vernis"]]
    reponse = client.post(f"{API}/reordonner", json={"ids": nouvel_ordre})
    assert reponse.status_code == 200
    assert [c["nom"] for c in reponse.json()] == ["Consommables", "Gels", "Capsules", "Vernis"]
    assert [c["ordre"] for c in client.get(API).json()] == [1, 2, 3, 4]


@pytest.mark.parametrize("modif", ["incomplete", "doublon", "inconnue"])
def test_reordonner_liste_invalide(client, modif):
    ids = list(_ids(client).values())
    corps = {"incomplete": ids[:3], "doublon": ids[:3] + [ids[0]], "inconnue": ids[:3] + [999]}[modif]
    reponse = client.post(f"{API}/reordonner", json={"ids": corps})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["code"] == "VALIDATION"


def test_supprimer_categorie_vide(client):
    id_capsules = _ids(client)["Capsules"]
    assert client.delete(f"{API}/{id_capsules}").status_code == 204
    assert "Capsules" not in _ids(client)


def test_supprimer_categorie_non_vide_refuse(client):
    id_gels = _ids(client)["Gels"]
    _ajouter_produit(client, id_gels, archive=True)  # les archivés comptent aussi
    reponse = client.delete(f"{API}/{id_gels}")
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "RESSOURCE_UTILISEE"
    assert reponse.json()["erreur"]["details"] == {"nb_produits": 1}


def test_supprimer_avec_fusion(client):
    ids = _ids(client)
    _ajouter_produit(client, ids["Gels"])
    _ajouter_produit(client, ids["Gels"], archive=True)
    reponse = client.delete(f"{API}/{ids['Gels']}", params={"fusionner_vers": ids["Vernis"]})
    assert reponse.status_code == 204
    vernis = next(c for c in client.get(API).json() if c["nom"] == "Vernis")
    assert vernis["nb_produits"] == 2


def test_fusion_vers_elle_meme_refusee(client):
    id_gels = _ids(client)["Gels"]
    assert client.delete(f"{API}/{id_gels}", params={"fusionner_vers": id_gels}).status_code == 422


def test_fusion_vers_inconnue(client):
    id_gels = _ids(client)["Gels"]
    assert client.delete(f"{API}/{id_gels}", params={"fusionner_vers": 999}).status_code == 404


def test_supprimer_inconnue(client):
    assert client.delete(f"{API}/999").status_code == 404
