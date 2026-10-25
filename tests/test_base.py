import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.database import initialiser_base
from app.models import Categorie, Inventaire, StatutInventaire


def test_categories_de_depart(session):
    noms = [c.nom for c in session.exec(select(Categorie).order_by(Categorie.ordre))]
    assert noms == ["Gels", "Vernis", "Capsules", "Consommables"]


def test_initialisation_idempotente(moteur, session):
    initialiser_base(moteur)
    initialiser_base(moteur)
    assert len(session.exec(select(Categorie)).all()) == 4


def test_nom_de_categorie_unique_sans_casse(session):
    session.add(Categorie(nom="gels", couleur_r=0, couleur_g=0, couleur_b=0))
    with pytest.raises(IntegrityError):
        session.commit()


def test_opacite_hors_bornes_refusee(session):
    session.add(Categorie(nom="Strass", couleur_r=0, couleur_g=0, couleur_b=0, couleur_a=0.1))
    with pytest.raises(IntegrityError):
        session.commit()


def test_un_seul_brouillon_a_la_fois(session):
    session.add(Inventaire(statut=StatutInventaire.valide))
    session.add(Inventaire(statut=StatutInventaire.brouillon))
    session.commit()
    session.add(Inventaire(statut=StatutInventaire.brouillon))
    with pytest.raises(IntegrityError):
        session.commit()
