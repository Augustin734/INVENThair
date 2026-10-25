import pytest
from sqlmodel import Session

from app.models import Produit, Unite

API = "/api/v1/fournisseurs"


def _creer(client, nom="Grossiste A", **autres):
    reponse = client.post(API, json={"nom": nom, **autres})
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def _rattacher_produit(client, fournisseur_id, archive=False):
    with Session(client.app.state.moteur) as s:
        s.add(Produit(nom="Essai", categorie_id=1, fournisseur_id=fournisseur_id, unite=Unite.ml, seuil_alerte=1, qte_reappro=1, archive=archive))
        s.commit()


def test_creer_et_lister_par_nom(client):
    _creer(client, "Nail Déco Shop")
    _creer(client, "grossiste B", email="b@grossiste.fr", notes="Commande le lundi")
    _creer(client, "Grossiste A", email="", site_url="  ")
    liste = client.get(API).json()
    assert [f["nom"] for f in liste] == ["Grossiste A", "grossiste B", "Nail Déco Shop"]
    assert liste[0]["email"] is None and liste[0]["site_url"] is None
    assert liste[1]["nb_produits"] == 0


def test_nom_en_double_refuse(client):
    _creer(client, "Grossiste A")
    reponse = client.post(API, json={"nom": "grossiste a"})
    assert reponse.status_code == 409
    assert reponse.json()["erreur"]["code"] == "NOM_DEJA_UTILISE"


@pytest.mark.parametrize("corps, champ", [({"nom": " "}, "nom"), ({"nom": "X", "email": "pas-un-mail"}, "email"), ({"nom": "X", "tel": "06"}, "tel")])
def test_creation_invalide(client, corps, champ):
    reponse = client.post(API, json=corps)
    assert reponse.status_code == 422
    assert champ in reponse.json()["erreur"]["details"]


def test_modifier_et_effacer_un_champ(client):
    f = _creer(client, email="a@grossiste.fr")
    reponse = client.patch(f"{API}/{f['id']}", json={"notes": "Livraison 48 h", "email": None})
    assert reponse.status_code == 200
    assert reponse.json()["notes"] == "Livraison 48 h"
    assert reponse.json()["email"] is None


def test_modifier_vers_nom_existant_refuse(client):
    _creer(client, "Grossiste A")
    b = _creer(client, "Grossiste B")
    assert client.patch(f"{API}/{b['id']}", json={"nom": "Grossiste A"}).status_code == 409


def test_modifier_inconnu(client):
    assert client.patch(f"{API}/999", json={"nom": "X"}).status_code == 404


def test_supprimer_fournisseur_libre(client):
    f = _creer(client)
    assert client.delete(f"{API}/{f['id']}").status_code == 204
    assert client.get(API).json() == []


def test_supprimer_fournisseur_utilise_refuse(client):
    f = _creer(client, "Grossiste B")
    _rattacher_produit(client, f["id"])
    _rattacher_produit(client, f["id"], archive=True)
    reponse = client.delete(f"{API}/{f['id']}")
    assert reponse.status_code == 409
    erreur = reponse.json()["erreur"]
    assert erreur["code"] == "RESSOURCE_UTILISEE"
    assert erreur["details"] == {"nb_produits": 2, "nb_archives": 1}
    assert "dont 1 archivé" in erreur["message"]


def test_supprimer_inconnu(client):
    assert client.delete(f"{API}/999").status_code == 404
