def test_health_repond_ok(client):
    reponse = client.get("/api/v1/health")
    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}


def test_route_inconnue_renvoie_introuvable(client):
    reponse = client.get("/api/v1/nexiste-pas")
    assert reponse.status_code == 404
    assert reponse.json() == {
        "erreur": {"code": "INTROUVABLE", "message": "Ce que tu cherches n'existe pas.", "details": {}}
    }


def test_mauvaise_methode_au_format_unique(client):
    reponse = client.post("/api/v1/health")
    assert reponse.status_code == 405
    assert reponse.json()["erreur"]["code"] == "METHODE_NON_AUTORISEE"


def test_page_accueil_servie(client):
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert "INVENT" in reponse.text


def test_routes_v2_reservees_absentes(client):
    assert client.get("/api/v1/disponibilites").status_code == 404
    assert client.post("/api/v1/ventes").status_code == 404
