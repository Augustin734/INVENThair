"""Envoi de la liste d'achat par mail avec le PDF en pièce jointe (US14)."""

import logging
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage

from app import schemas
from app.config import Reglages
from app.erreurs import ErreurMetier
from app.services.exports import a_commander, nom_fichier
from app.services.textes import date_fr, quantite_fr

journal = logging.getLogger("inventhair")
DELAI_SECONDES = 15


def _echec(message: str, raison: str) -> ErreurMetier:
    return ErreurMetier(502, "ENVOI_MAIL_ECHOUE", message, {"raison": raison})


def composer(reglages: Reglages, destinataire: str, liste: schemas.ListeAchat, pdf: bytes, moment: datetime) -> EmailMessage:
    groupes = a_commander(liste)
    nb = sum(len(g.lignes) for g in groupes)
    corps = [f"Bonjour,", "", f"Voici la liste d'achat du {date_fr(moment)} : {nb} produit{'s' if nb > 1 else ''} à racheter.", ""]
    for groupe in groupes:
        corps.append(groupe.nom if groupe.fournisseur_id is None else f"Chez {groupe.nom}")
        corps += [f"  - {l.nom} : {quantite_fr(l.quantite, l.unite.value)}" for l in groupe.lignes]
        corps.append("")
    corps += ["Le détail est dans le PDF joint.", "", "INVENThair"]

    message = EmailMessage()
    message["Subject"] = f"Liste d'achat du {moment:%d/%m/%Y}"
    message["From"] = reglages.smtp_expediteur
    message["To"] = destinataire
    message.set_content("\n".join(corps))
    message.add_attachment(pdf, maintype="application", subtype="pdf", filename=nom_fichier(moment, "pdf"))
    return message


def envoyer(reglages: Reglages, message: EmailMessage) -> None:
    if not reglages.envoi_mail_configure:
        raise _echec("L'envoi par mail n'est pas encore réglé : complète la partie SMTP du fichier .env.", "non_configure")
    contexte = ssl.create_default_context()
    try:
        if reglages.smtp_securite == "ssl":
            serveur = smtplib.SMTP_SSL(reglages.smtp_hote, reglages.smtp_port, timeout=DELAI_SECONDES, context=contexte)
        else:
            serveur = smtplib.SMTP(reglages.smtp_hote, reglages.smtp_port, timeout=DELAI_SECONDES)
        with serveur:
            if reglages.smtp_securite == "starttls":
                serveur.starttls(context=contexte)
            if reglages.smtp_utilisateur:
                serveur.login(reglages.smtp_utilisateur, reglages.smtp_mot_de_passe)
            serveur.send_message(message)
    except smtplib.SMTPAuthenticationError as exc:
        journal.warning("SMTP : authentification refusée (%s)", exc)
        raise _echec("Le serveur mail a refusé l'identifiant ou le mot de passe du fichier .env.", "authentification") from exc
    except smtplib.SMTPRecipientsRefused as exc:
        journal.warning("SMTP : destinataire refusé (%s)", exc)
        raise _echec(f"Le serveur mail refuse l'adresse {message['To']}. Vérifie-la.", "destinataire") from exc
    except smtplib.SMTPException as exc:
        journal.warning("SMTP : envoi refusé (%s)", exc)
        raise _echec("Le serveur mail a refusé l'envoi. Réessaie dans un moment.", "refus") from exc
    except OSError as exc:  # pas de réseau, serveur injoignable, délai dépassé
        journal.warning("SMTP : serveur injoignable (%s)", exc)
        raise _echec("Impossible de joindre le serveur mail. Vérifie la connexion internet.", "connexion") from exc
