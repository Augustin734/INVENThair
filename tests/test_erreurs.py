from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.erreurs import ErreurMetier, installer_gestionnaires


class Corps(BaseModel):
    quantite: float


def _app_essai() -> TestClient:
    app = FastAPI()
    installer_gestionnaires(app)

    @app.post("/essai")
    def essai(corps: Corps):
        if corps.quantite < 0:
            raise ErreurMetier(409, "STOCK_INSUFFISANT", "Pas assez de stock.", {"disponible": 3})
        return {"ok": True}

    @app.get("/plantage")
    def plantage():
        raise RuntimeError("boum")

    return TestClient(app, raise_server_exceptions=False)


def test_erreur_metier_au_format_unique():
    reponse = _app_essai().post("/essai", json={"quantite": -1})
    assert reponse.status_code == 409
    assert reponse.json() == {
        "erreur": {"code": "STOCK_INSUFFISANT", "message": "Pas assez de stock.", "details": {"disponible": 3}}
    }


def test_validation_detaillee_par_champ():
    reponse = _app_essai().post("/essai", json={"quantite": "beaucoup"})
    assert reponse.status_code == 422
    erreur = reponse.json()["erreur"]
    assert erreur["code"] == "VALIDATION"
    assert "quantite" in erreur["details"]


def test_erreur_inattendue_masquee():
    reponse = _app_essai().get("/plantage")
    assert reponse.status_code == 500
    assert reponse.json()["erreur"]["code"] == "ERREUR_INTERNE"
    assert "boum" not in reponse.text
