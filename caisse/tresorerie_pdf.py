import os
from datetime import datetime
from collections import defaultdict

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Table,
    TableStyle,
    Spacer,
    Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle

class TresoreriePDF:

    def __init__(self, entreprise, logo_path=None, devise="CFA"):
        self.entreprise = entreprise
        self.logo_path = logo_path
        self.devise = devise
        self.styles = getSampleStyleSheet()
        self.cell_style = ParagraphStyle(
            name="CellStyle",
            fontSize=9,
            leading=11,
            wordWrap="CJK"   # 🔥 empêche le chevauchement
        )

    def generer(self, fichier, rows, periode, totaux):
        doc = SimpleDocTemplate(
            fichier,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm
        )

        elements = []

        # ===== EN-TÊTE =====
        header = []

        if self.logo_path and os.path.exists(self.logo_path):
            header.append(Image(self.logo_path, 3 * cm, 3 * cm))
        else:
            header.append(Paragraph("", self.styles["Normal"]))

        header.append(Paragraph(
            f"<b>{self.entreprise}</b><br/>"
            f"Rapport de Trésorerie<br/>"
            f"Période : {periode}<br/>"
            f"Édité le : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            self.styles["Normal"]
        ))

        elements.append(Table([header], colWidths=[4 * cm, 12 * cm]))
        elements.append(Spacer(1, 20))

        # ===== REGROUPEMENT PAR COMPTE =====
        comptes = defaultdict(list)
        for row in rows:
            # row = (date, type, libellé, montant, compte, solde)
            comptes[row[4]].append(row)

        # ===== TABLEAUX PAR COMPTE =====
        for compte, lignes in comptes.items():

            elements.append(Spacer(1, 15))
            elements.append(Paragraph(
                f"<b>Compte : {compte}</b>",
                self.styles["Heading3"]
            ))

            data = [["Date", "Type", "Libellé", "Montant", "Solde"]]
            solde_final = 0

            for d, t, l, m, c, s in lignes:
                solde_final = s
                data.append([
                    Paragraph(str(d), self.cell_style),
                    Paragraph(str(t), self.cell_style),
                    Paragraph(str(l), self.cell_style),   # 👈 clé du problème
                    Paragraph(f"{m:,.0f} {self.devise}", self.cell_style),
                    Paragraph(f"{s:,.0f} {self.devise}", self.cell_style),
                ])

            table = Table(
                data,
                repeatRows=1,
                colWidths=[2.5 * cm, 4.5 * cm, 3 * cm, 3 * cm, 3 * cm]

            )

            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
            ]))

            elements.append(table)

            # --- Solde du compte ---
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(
                f"<b>Solde {compte} : {solde_final:,.0f} {self.devise}</b>",
                self.styles["Normal"]
            ))

        # ===== SYNTHÈSE GÉNÉRALE =====
        elements.append(Spacer(1, 25))
        elements.append(Paragraph(
            "<b>Synthèse Générale</b>",
            self.styles["Heading2"]
        ))

        total_entrees, total_sorties, solde_global = totaux

        elements.append(Paragraph(
            f"""
            Total Entrées : {total_entrees:,.0f} {self.devise}<br/>
            Total Sorties : {total_sorties:,.0f} {self.devise}<br/>
            <b>Solde Global : {solde_global:,.0f} {self.devise}</b>
            """,
            self.styles["Normal"]
        ))

        doc.build(elements)
