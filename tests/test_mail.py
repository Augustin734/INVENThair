import smtplib
from email import message_from_bytes, policy

import pytest

from app.services import mail

API = "/api/v1/liste-achat/envoyer"
VARIABLES = ["SMTP_HOTE", "SMTP_PORT", "SMTP_SECURITE", "SMTP_UTILISATEUR", "SMTP_MOT_DE_PASSE", "SMTP_EXPEDITEUR", "MAIL_DESTINATAIRE_DEFAUT"]


class FauxSMTP:
    """Remplace smtplib.SMTP / SMTP_SSL : enregistre les échanges, peut simuler une panne."""

    instances: list["FauxSMTP"] = []
    panne: Exception | None = None

    def __init__(self, hote, port, timeout=None, context=None):
        if FauxSMTP.panne is not None and isinstance(FauxSMTP.panne, OSError):
            raise FauxSMTP.panne
        self.hote, self.port, self.ssl = hote, port, context is not None
        self.starttls_fait, self.identifiants, self.messages = False, None, []
        FauxSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.starttls_fait = True

    def login(self, utilisateur, mot_de_passe):
        if isinstance(FauxSMTP.panne, smtplib.SMTPAuthenticationError):
            raise FauxSMTP.panne
        self.identifiants = (utilisateur, mot_de_passe)

    def send_message(self, message):
        if FauxSMTP.panne is not None:
            raise FauxSMTP.panne
        self.messages.append(message)


@pytest.fixture(autouse=True)
def environnement_propre(monkeypatch):
    for variable in VARIABLES:
        monkeypatch.delenv(variable, raising=False)
    FauxSMTP.instances, FauxSMTP.panne = [], None
    monkeypatch.setattr(mail.smtplib, "SMTP", FauxSMTP)
    monkeypatch.setattr(mail.smtplib, "SMTP_SSL", FauxSMTP)


@pytest.fixture
def smtp_configure(monkeypatch):
    monkeypatch.setenv("SMTP_HOTE", "smtp.exemple.fr")
    monkeypatch.setenv("SMTP_UTILISATEUR", "maud")
    monkeypatch.setenv("SMTP_MOT_DE_PASSE", "secret")
    monkeypatch.setenv("SMTP_EXPEDITEUR", "INVENThair <stock@onglerie.fr>")


@pytest.fixture
def liste(client):
    f = client.post("/api/v1/fournisseurs", json={"nom": "Grossiste A"}).json()["id"]
    corps = {"nom": "Gel builder clair", "categorie_id": 1, "fournisseur_id": f, "unite": "ml", "seuil_alerte": 50, "qte_reappro": 100, "stock_initial": 35}
    client.post("/api/v1/produits", json=corps)
    return client.get("/api/v1/liste-achat").json()


# ---------- GET /parametres ----------

def test_parametres_par_defaut(client):
    reponse = client.get("/api/v1/parametres")
    assert reponse.status_code == 200
    assert reponse.json() == {"mail_destinataire_defaut": None, "envoi_mail_configure": False}


def test_parametres_depuis_env_sans_secret(client, smtp_configure, monkeypatch):
    monkeypatch.setenv("MAIL_DESTINATAIRE_DEFAUT", "maud@onglerie.fr")
    reponse = client.get("/api/v1/parametres")
    assert reponse.json() == {"mail_destinataire_defaut": "maud@onglerie.fr", "envoi_mail_configure": True}
    assert "secret" not in reponse.text


def test_parametres_mauvaise_methode(client):
    assert client.post("/api/v1/parametres").status_code == 405


# ---------- POST /liste-achat/envoyer ----------

def test_envoi_nominal(client, liste, smtp_configure):
    reponse = client.post(API, json={"destinataire": "maud@onglerie.fr", "liste": liste})
    assert reponse.status_code == 202
    assert reponse.json()["destinataire"] == "maud@onglerie.fr"
    assert reponse.json()["nb_produits"] == 1

    serveur = FauxSMTP.instances[0]
    assert (serveur.hote, serveur.port, serveur.starttls_fait, serveur.identifiants) == ("smtp.exemple.fr", 587, True, ("maud", "secret"))
    envoye = message_from_bytes(serveur.messages[0].as_bytes(), policy=policy.default)
    assert envoye["To"] == "maud@onglerie.fr"
    assert envoye["Subject"].startswith("Liste d'achat du ")
    texte, piece = [p for p in envoye.walk() if not p.is_multipart()]
    assert "Gel builder clair : 100 ml" in texte.get_content()
    assert piece.get_filename().startswith("liste-achat-") and piece.get_payload(decode=True).startswith(b"%PDF-")


def test_envoi_en_ssl_sur_le_port_465(client, liste, smtp_configure, monkeypatch):
    monkeypatch.setenv("SMTP_PORT", "465")
    assert client.post(API, json={"destinataire": "maud@onglerie.fr", "liste": liste}).status_code == 202
    serveur = FauxSMTP.instances[0]
    assert (serveur.port, serveur.ssl, serveur.starttls_fait) == (465, True, False)


def test_envoi_non_configure(client, liste):
    reponse = client.post(API, json={"destinataire": "maud@onglerie.fr", "liste": liste})
    assert reponse.status_code == 502
    assert reponse.json()["erreur"]["code"] == "ENVOI_MAIL_ECHOUE"
    assert reponse.json()["erreur"]["details"] == {"raison": "non_configure"}


@pytest.mark.parametrize(
    "panne, raison",
    [
        (OSError("réseau coupé"), "connexion"),
        (smtplib.SMTPAuthenticationError(535, b"refus"), "authentification"),
        (smtplib.SMTPRecipientsRefused({"x@y.fr": (550, b"inconnu")}), "destinataire"),
        (smtplib.SMTPDataError(554, b"spam"), "refus"),
    ],
)
def test_envoi_en_echec(client, liste, smtp_configure, panne, raison):
    FauxSMTP.panne = panne
    reponse = client.post(API, json={"destinataire": "maud@onglerie.fr", "liste": liste})
    assert reponse.status_code == 502
    erreur = reponse.json()["erreur"]
    assert (erreur["code"], erreur["details"]["raison"]) == ("ENVOI_MAIL_ECHOUE", raison)
    assert "secret" not in erreur["message"]


def test_destinataire_invalide(client, liste, smtp_configure):
    reponse = client.post(API, json={"destinataire": "maud", "liste": liste})
    assert reponse.status_code == 422
    assert reponse.json()["erreur"]["details"]["destinataire"] == "Adresse mail invalide."
    assert FauxSMTP.instances == []


def test_liste_vide_refusee(client, smtp_configure):
    reponse = client.post(API, json={"destinataire": "maud@onglerie.fr", "liste": {"fournisseurs": []}})
    assert reponse.status_code == 422
    assert "liste" in reponse.json()["erreur"]["details"]
