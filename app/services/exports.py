"""Exports de la liste d'achat en CSV et en PDF (US13). Le PDF sert aussi de pièce jointe au mail (US14)."""

import csv
import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app import schemas
from app.services.textes import date_fr, nombre_fr, quantite_fr, unite_fr

PRUNE = colors.HexColor("#430D2B")
MAUVE = colors.HexColor("#79365C")
PIVOINE = colors.HexColor("#B01050")
ROSE_PALE = colors.HexColor("#FCD4E6")
ENCRE = colors.HexColor("#270317")

# Polices intégrées à ReportLab (encodage WinAnsi : accents, « », œ). Les polices de la charte arriveront avec le front.
POLICE, POLICE_GRASSE = "Helvetica", "Helvetica-Bold"


def nom_fichier(moment: datetime, extension: str) -> str:
    return f"liste-achat-{moment:%Y-%m-%d}.{extension}"


def a_commander(liste: schemas.ListeAchat) -> list[schemas.GroupeFournisseur]:
    """Retire les lignes à quantité 0 et les groupes devenus vides."""
    groupes = []
    for groupe in liste.fournisseurs:
        lignes = [l for l in groupe.lignes if l.quantite > 0]
        if lignes:
            groupes.append(groupe.model_copy(update={"lignes": lignes}))
    return groupes


def generer_csv(liste: schemas.ListeAchat) -> bytes:
    """Séparateur « ; », virgule décimale et BOM UTF-8 : s'ouvre directement dans un tableur français."""
    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, delimiter=";", lineterminator="\r\n")
    ecrivain.writerow(["Fournisseur", "Produit", "Unité", "Stock actuel", "Seuil d'alerte", "Quantité à commander"])
    for groupe in a_commander(liste):
        for l in groupe.lignes:
            ecrivain.writerow([groupe.nom, l.nom, unite_fr(l.unite.value, 1), nombre_fr(l.stock_actuel), nombre_fr(l.seuil_alerte), nombre_fr(l.quantite)])
    return tampon.getvalue().encode("utf-8-sig")


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "titre": ParagraphStyle("titre", fontName=POLICE_GRASSE, fontSize=24, leading=28, textColor=PRUNE),
        "sous_titre": ParagraphStyle("sous_titre", fontName=POLICE_GRASSE, fontSize=11, leading=15, textColor=MAUVE, spaceBefore=4),
        "groupe": ParagraphStyle("groupe", fontName=POLICE_GRASSE, fontSize=14, leading=18, textColor=PIVOINE, spaceBefore=14),
        "contact": ParagraphStyle("contact", fontName=POLICE, fontSize=9.5, leading=12, textColor=MAUVE, spaceAfter=4),
        "cellule": ParagraphStyle("cellule", fontName=POLICE, fontSize=10.5, leading=13, textColor=ENCRE),
        "vide": ParagraphStyle("vide", fontName=POLICE_GRASSE, fontSize=13, leading=18, textColor=MAUVE, spaceBefore=18),
    }


def _tableau(groupe: schemas.GroupeFournisseur, style_cellule: ParagraphStyle) -> Table:
    donnees = [["Produit", "Reste", "Seuil", "À commander"]]
    for l in groupe.lignes:
        donnees.append([
            Paragraph(escape(l.nom), style_cellule),
            quantite_fr(l.stock_actuel, l.unite.value),
            quantite_fr(l.seuil_alerte, l.unite.value),
            quantite_fr(l.quantite, l.unite.value),
        ])
    tableau = Table(donnees, colWidths=[82 * mm, 29 * mm, 29 * mm, 34 * mm], repeatRows=1)
    tableau.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRUNE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), POLICE_GRASSE),
        ("FONTNAME", (1, 1), (-1, -1), POLICE),
        ("FONTNAME", (3, 1), (3, -1), POLICE_GRASSE),
        ("FONTSIZE", (0, 0), (-1, -1), 10.5),
        ("TEXTCOLOR", (1, 1), (-1, -1), ENCRE),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROSE_PALE]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.6, MAUVE),
        ("BOX", (0, 0), (-1, -1), 1.2, PRUNE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tableau


def generer_pdf(liste: schemas.ListeAchat, moment: datetime, emails: dict[int, str] | None = None) -> bytes:
    """A4 aux couleurs de la charte : un bloc par fournisseur (avec son mail s'il est connu)."""
    emails = emails or {}
    styles = _styles()
    groupes = a_commander(liste)
    nb_produits = sum(len(g.lignes) for g in groupes)

    contenu = [
        Paragraph("Ta liste d'achat", styles["titre"]),
        Paragraph(
            f"Générée le {date_fr(moment)} · {nb_produits} produit{'s' if nb_produits > 1 else ''} à racheter",
            styles["sous_titre"],
        ),
        Spacer(1, 4 * mm),
    ]
    if not groupes:
        contenu.append(Paragraph("Rien à racheter pour l'instant !", styles["vide"]))
    for groupe in groupes:
        titre = escape(groupe.nom) if groupe.fournisseur_id is None else f"Chez {escape(groupe.nom)}"
        bloc = [Paragraph(titre, styles["groupe"])]
        if groupe.fournisseur_id in emails:
            bloc.append(Paragraph(escape(emails[groupe.fournisseur_id]), styles["contact"]))
        bloc.append(_tableau(groupe, styles["cellule"]))
        contenu.append(KeepTogether(bloc))

    def pied_de_page(canevas, document):
        canevas.saveState()
        canevas.setFont(POLICE, 8.5)
        canevas.setFillColor(MAUVE)
        canevas.drawString(document.leftMargin, 10 * mm, f"INVENThair · liste d'achat du {moment:%d/%m/%Y}")
        canevas.drawRightString(A4[0] - document.rightMargin, 10 * mm, f"page {document.page}")
        canevas.restoreState()

    tampon = io.BytesIO()
    document = SimpleDocTemplate(
        tampon, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
        title="Liste d'achat", author="INVENThair", subject=nom_fichier(moment, "pdf"),
    )
    document.build(contenu, onFirstPage=pied_de_page, onLaterPages=pied_de_page)
    return tampon.getvalue()
