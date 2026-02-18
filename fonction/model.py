import os
from PySide6.QtCore import Qt
from jinja2 import Environment, FileSystemLoader
try:
    from num2words import num2words
except:
    pass
import bcrypt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import datetime
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image
)
from reportlab.lib import colors
import locale
locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
def hash_password(password):
    """Hache le mot de passe avec un sel."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
def check_password(input_password, stored_hashed_password):
    """Vérifie le mot de passe saisi par rapport au hash stocké."""
    return bcrypt.checkpw(input_password.encode('utf-8'), stored_hashed_password)
class Model:    
    def __init__(self) -> None:
        super().__init__()

        self.env = Environment(loader=FileSystemLoader('template'))

        # La fonction principale
     
    def facture_donnees(
    self, Entr, T1, T2, info, ville, adresse, responsabable,
    list_article, vente, msg, remarque, ifu, autre, date, taux,devise,chemin=None,sign=None,cahet=None
):
        ht = 0.0   
        for j in list_article:
            ht += float(j[3])

        mnt_ttc = ht * (1 + (float(taux) / 100))
        net = float(mnt_ttc)

        try:
            lettre = num2words(net, lang='fr')
        except Exception:
            lettre = ""

        return {
            "entreprise": {
                "nom": Entr,
                "tel1": T1,
                "tel2": T2,
                "info": info,
                "ville": ville,
                "adresse": adresse,
                "resp": responsabable,
                "ifu": ifu,
                "autre": autre
            },
            "liste_article": list_article,
            "vente": vente,
            "msg": msg,
            "ht": ht,
            "ttc": mnt_ttc,
            "net": net,
            "lettre": lettre,
            "chemin": chemin,
            "signature":sign,
            "cahet":cahet,
            "remarque": remarque,
            "date": date,
            "devise":devise,
        }
    
    def generer_facture_pdf_reportlab(self, donnees, chemin_pdf):

        try:
            doc = SimpleDocTemplate(
                chemin_pdf,
                pagesize=A4,
                rightMargin=1.2*cm,
                leftMargin=1.2*cm,
                topMargin=1.2*cm,
                bottomMargin=1.2*cm
            )

            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name="Titre",
                fontSize=14,
                alignment=1,
                spaceAfter=8
            ))

            elements = []

            # ─────────────────────────────
            # 🟦 EN-TÊTE
            # ─────────────────────────────
            header_data = []

            if donnees.get("chemin") and os.path.exists(donnees["chemin"]):
                logo = Image(donnees["chemin"], width=2.5*cm, height=2.5*cm)
            else:
                logo = ""

            header_data.append([
                logo,
                Paragraph(
                    f"<b>{donnees['entreprise']['nom']}</b><br/>"
                    f"Tél : {donnees['entreprise']['tel1']} / {donnees['entreprise']['tel2']}<br/>"
                    f"IFU : {donnees['entreprise']['ifu']}<br/>"
                    f"{donnees['entreprise']['info']}<br/>"
                    f"{donnees['entreprise']['ville']} - {donnees['entreprise']['adresse']}",
                    styles["Normal"]
                )
            ])

            elements.append(Table(header_data, colWidths=[4*cm, 12*cm]))
            elements.append(Spacer(1, 12))

            # ─────────────────────────────
            # 👤 CLIENT / FACTURE
            # ─────────────────────────────
            info_table = Table([
                [
            Paragraph(
                "<b>Information du client</b><br/>"
                f"Nom : {donnees['vente']['nom']}<br/>"
                f"Ville : {donnees['vente']['ville']}<br/>"
                f"Tél : {donnees['vente']['Contact']}",
                styles["Normal"]
            ),
            Paragraph(
                f"<b>{donnees['msg']}</b><br/>"
                f"<b>N° :</b> {donnees['vente']['facture']}<br/>",
                styles["Normal"]
            )]
            ], colWidths=[8*cm, 9*cm])
            info_table.setStyle(TableStyle([
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("ALIGN", (1,0), (1,0), "RIGHT"),

                # 🔲 Encadrement uniquement du bloc facture
                ("BOX", (1,0), (1,0), 1, colors.black),
                ("BACKGROUND", (1,0), (1,0), colors.whitesmoke),
                ("LEFTPADDING", (1,0), (1,0), 8),
                ("RIGHTPADDING", (1,0), (1,0), 8),
                ("TOPPADDING", (1,0), (1,0), 6),
                ("BOTTOMPADDING", (1,0), (1,0), 6),
            ]))

            elements.append(info_table)
            elements.append(Spacer(1, 12))

            # ─────────────────────────────
            # 📦 ARTICLES
            # ─────────────────────────────
            table_data = [["N°", "Désignation", "Qté", "PU", "Montant"]]

            for i, l in enumerate(donnees["liste_article"], start=1):
                qte = float(l[1])
                pu = float(l[2])
                montant = float(l[3])
                table_data.append([
                    i,
                    l[0],
                    int(qte),
                    f"{pu:,.0f}".replace(",", " "),
                    f"{montant:,.0f}".replace(",", " ")
                ])

            table_data += [
                ["", "", "", "HT", f"{donnees['ht']:,.0f}"],
                ["", "", "", "TTC", f"{donnees['ttc']:,.0f}"],
                ["", "", "", "Net à payer", f"{donnees['net']:,.0f}"],
            ]

            t = Table(table_data, colWidths=[1.2*cm, 7*cm, 2*cm, 2.5*cm, 3.3*cm])
            t.setStyle(TableStyle([
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                ("ALIGN", (2,1), (-1,-1), "RIGHT"),
                ("FONT", (0,0), (-1,0), "Helvetica-Bold")
            ]))
            elements.append(t)
            # ─────────────────────────────
            # 💳 PAIEMENT
            # ─────────────────────────────
            if donnees["vente"]["type_facture"] == "Facture":
                paiement_table = Table([
                    [
                        f"Montant versé : {donnees['vente']['mont_verse']:,.0f} {donnees['devise']}",
                        f"Reste à payer : {donnees['vente']['reste']:,.0f} {donnees['devise']}"
                    ]
                ], colWidths=[8*cm, 8*cm])

                paiement_table.setStyle(TableStyle([
                    ("ALIGN", (0,0), (0,0), "LEFT"),
                    ("ALIGN", (1,0), (1,0), "RIGHT"),
                    ("FONT", (0,0), (-1,-1), "Helvetica-Bold"),
                    ("TOPPADDING", (0,0), (-1,-1), 6),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ]))

                elements.append(Spacer(1, 10))
                elements.append(paiement_table)

            # ─────────────────────────────
            # 📝 REMARQUES
            # ─────────────────────────────
            remarque = donnees.get("remarque")
            if remarque:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph("<b>Remarque :</b>", styles["Normal"]))
                elements.append(Paragraph(str(remarque), styles["Normal"]))
            elements.append(Spacer(1, 40))
            # ─────────────────────────────
            # ✍️ DATE – RESPONSABLE – CACHET – SIGNATURE (À DROITE)
            # ─────────────────────────────
            elements.append(Spacer(1, 40))

            signature_img = None
            cachet_img = None

            if donnees.get("signature") and os.path.exists(donnees["signature"]):
                signature_img = Image(donnees["signature"], width=4*cm, height=2*cm)

            if donnees.get("cachet") and os.path.exists(donnees["cachet"]):
                cachet_img = Image(donnees["cachet"], width=4*cm, height=4*cm)

            signature_table = Table([
                [
                    "",
                    Paragraph(
                        f"Fait à {donnees['entreprise']['ville']}, le {donnees['vente']['date']}<br/><br/>",
                styles["Normal"]
                    )
                ],
                [
                    "",
                    Paragraph(
                        f"<b>{donnees['entreprise']['resp']}</b>",
                        styles["Normal"]
                    )
                ],
                [
                    "",
                    cachet_img if cachet_img else ""
                ],
                [
                    "",
                    signature_img if signature_img else ""
                ],
            ], colWidths=[9*cm, 7*cm])

            signature_table.setStyle(TableStyle([
                ("ALIGN", (1,0), (1,-1), "RIGHT"),
                ("VALIGN", (1,0), (1,-1), "TOP"),
                ("TOPPADDING", (1,0), (1,-1), 6),
                ("BOTTOMPADDING", (1,0), (1,-1), 6),
            ]))

            elements.append(signature_table)
            doc.build(elements)
        except Exception as e:
            print("❌ ERREUR PDF :", e)
            raise
   
