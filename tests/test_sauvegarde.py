import sqlite3
import subprocess
import sys
from pathlib import Path

from app.services import sauvegarde

RACINE = Path(__file__).resolve().parent.parent


def test_backup_cree_une_copie_datee(client, chemin_base):
    client.post("/api/v1/fournisseurs", json={"nom": "Grossiste A"})
    reponse = client.post("/api/v1/backup")
    assert reponse.status_code == 201
    fichier = reponse.json()["fichier"]
    assert fichier.startswith("test-") and fichier.endswith(".db")

    copie = chemin_base.parent / "backups" / fichier
    with sqlite3.connect(copie) as connexion:
        assert connexion.execute("select nom from fournisseur").fetchall() == [("Grossiste A",)]


def test_deux_sauvegardes_dans_la_meme_seconde(client):
    noms = {client.post("/api/v1/backup").json()["fichier"] for _ in range(3)}
    assert len(noms) == 3


def test_backup_mauvaise_methode(client):
    assert client.get("/api/v1/backup").json()["erreur"]["code"] == "METHODE_NON_AUTORISEE"


def test_sauvegarde_en_ligne_de_commande(moteur, chemin_base):
    resultat = subprocess.run(
        [sys.executable, "-m", "app.services.sauvegarde"], cwd=RACINE, capture_output=True, text=True,
        env={"INVENTHAIR_DB": str(chemin_base), "PATH": "/usr/bin:/bin"},
    )
    assert resultat.returncode == 0, resultat.stderr
    assert "Sauvegarde créée" in resultat.stdout
    assert len(list(sauvegarde.dossier_sauvegardes(chemin_base).glob("*.db"))) == 1


def test_sauvegarde_sans_base(tmp_path):
    resultat = subprocess.run(
        [sys.executable, "-m", "app.services.sauvegarde"], cwd=RACINE, capture_output=True, text=True,
        env={"INVENTHAIR_DB": str(tmp_path / "absente.db"), "PATH": "/usr/bin:/bin"},
    )
    assert resultat.returncode == 1
    assert "Pas de base à sauvegarder" in resultat.stderr
