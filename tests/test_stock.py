import pytest
from sqlmodel import select

from app.erreurs import ErreurMetier
from app.models import Mouvement, Produit, TypeMouvement, Unite
from app.services.stock import appliquer_mouvement


@pytest.fixture
def produit(session):
    p = Produit(nom="Gel builder clair", categorie_id=1, unite=Unite.ml, seuil_alerte=50, qte_reappro=100)
    session.add(p)
    session.commit()
    return p


def test_entree_puis_sortie(session, produit):
    appliquer_mouvement(session, produit, TypeMouvement.entree, 100, "Réception commande")
    appliquer_mouvement(session, produit, TypeMouvement.sortie, 15, "Perte")
    session.commit()
    assert produit.stock_actuel == 85
    quantites = [m.quantite for m in session.exec(select(Mouvement).order_by(Mouvement.id))]
    assert quantites == [100, -15]


def test_ajustement_signe(session, produit):
    appliquer_mouvement(session, produit, TypeMouvement.entree, 10)
    appliquer_mouvement(session, produit, TypeMouvement.ajustement, -4)
    assert produit.stock_actuel == 6


def test_arrondi_des_decimales(session, produit):
    appliquer_mouvement(session, produit, TypeMouvement.entree, 0.1)
    appliquer_mouvement(session, produit, TypeMouvement.entree, 0.2)
    assert produit.stock_actuel == 0.3


def test_sortie_refusee_si_stock_insuffisant(session, produit):
    appliquer_mouvement(session, produit, TypeMouvement.entree, 35)
    with pytest.raises(ErreurMetier) as erreur:
        appliquer_mouvement(session, produit, TypeMouvement.sortie, 50)
    assert erreur.value.code == "STOCK_INSUFFISANT"
    assert erreur.value.details["disponible"] == 35
    assert produit.stock_actuel == 35


def test_quantite_nulle_refusee(session, produit):
    with pytest.raises(ErreurMetier) as erreur:
        appliquer_mouvement(session, produit, TypeMouvement.entree, 0)
    assert erreur.value.code == "VALIDATION"


def test_produit_archive_refuse(session, produit):
    produit.archive = True
    with pytest.raises(ErreurMetier) as erreur:
        appliquer_mouvement(session, produit, TypeMouvement.entree, 5)
    assert erreur.value.code == "PRODUIT_ARCHIVE"
