import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QAbstractItemView,
     QLabel, QHeaderView,QMessageBox
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
import sqlite3 as sq
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, Image
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import datetime
import sqlite3 as sq
from datetime import datetime
from fonction.methode import cal
from piece.compl import get_pdf_directory

class AnalyseEcartsDialog(QDialog):
    def __init__(self, db_path, inventory_id, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.inventory_id = inventory_id
        self.cal = cal()
        self.setWindowTitle("Analyse des écarts d'inventaire")
        self.setWindowIcon(QIcon(":/icon/icone.png"))
        self.resize(900, 450)

        # ================= TABLE =================
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Produit", "Théorique", "Réel", "Écart", "%", "Type", "Gravité"
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)

        # ================= INFOS =================
        self.lbl_resume = QLabel()
        self.lbl_resume.setAlignment(Qt.AlignmentFlag.AlignRight)

        # ================= BOUTONS =================
        self.btn_print = QPushButton("Générer PDF")
        
        self.btn_print.clicked.connect(self.generer_pdf_)
        self.btn_close = QPushButton("Fermer")
        self.btn_close.clicked.connect(self.close)

        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(self.btn_print)
        btns.addWidget(self.btn_close)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(self.lbl_resume)
        layout.addLayout(btns)

        self.charger_ecarts()

    # ======================================================
    def charger_ecarts(self):
        self.table.setRowCount(0)
        total_ecart_pos = 0
        total_ecart_neg = 0
        nb_ecarts = 0

        with sq.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    p.name,
                    s.qty,
                    l.qty_reelle,
                    (l.qty_reelle - s.qty) AS ecart
                FROM inventory_items l
                JOIN products p ON p.ref = l.product_ref
                JOIN stock s ON s.id_libelle = p.ref
                WHERE l.inventory_id = ?
            """, (self.inventory_id,))

            rows = cur.fetchall()

        for row_idx, (name, theo, reel, ecart) in enumerate(rows):
            self.table.insertRow(row_idx)

            pourcent = (ecart / theo * 100) if theo else 0

            if ecart > 0:
                type_ecart = "Surplus"
            elif ecart < 0:
                type_ecart = "Manquant"
            else:
                type_ecart = "OK"

            # Gravité (règle pro simple)
            if abs(pourcent) < 2:
                gravite = "Faible"
                color = Qt.GlobalColor.green
            elif abs(pourcent) < 10:
                gravite = "Moyenne"
                color = Qt.GlobalColor.yellow
            else:
                gravite = "Critique"
                color = Qt.GlobalColor.red

            values = [
                name, theo, reel, ecart,
                f"{pourcent:.1f}%", type_ecart, gravite
            ]

            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if col == 6:  # Gravité
                    item.setBackground(color)
                self.table.setItem(row_idx, col, item)

            if ecart != 0:
                nb_ecarts += 1
                if ecart > 0:
                    total_ecart_pos += ecart
                else:
                    total_ecart_neg += ecart

        self.lbl_resume.setText(
            f"Produits avec écart : {nb_ecarts} | "
            f"Surplus total : {total_ecart_pos} | "
            f"Manquant total : {total_ecart_neg}"
        )

  


    def generer_pdf_ecarts(self,
        db_path,
        inventory_id,
        fichier_pdf,
        logo_path,
        nom_entreprise="",
        utilisateur=""
    ):
        styles = getSampleStyleSheet()

        # Styles personnalisés
        style_titre = ParagraphStyle(
            "Titre",
            parent=styles["Normal"],
            fontSize=16,
            leading=20,
            spaceAfter=6,
            fontName="Helvetica-Bold"
        )

        style_info = ParagraphStyle(
            "Info",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.grey
        )

        elements = []

        # ================= EN-TÊTE =================
        logo = Image(logo_path, width=3*cm, height=3*cm)

        header_right = Paragraph(
            f"""
            <b>{nom_entreprise}</b><br/>
            <font size="12"><b>Rapport d’écarts d’inventaire</b></font><br/>
            Inventaire N° {inventory_id}<br/>
            Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}
            """,
            styles["Normal"]
        )

        header = Table(
            [[logo, header_right]],
            colWidths=[4*cm, 12*cm]
        )

        header.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ]))

        elements.append(header)
        elements.append(Spacer(1, 6))

        # Ligne de séparation
        elements.append(Table(
            [[""]],
            colWidths=[16*cm],
            style=[("LINEBELOW", (0,0), (-1,-1), 1, colors.black)]
        ))
        elements.append(Spacer(1, 12))

        # ================= INFOS =================
        elements.append(Paragraph(
            f"Utilisateur : <b>{utilisateur}</b>",
            style_info
        ))
        elements.append(Spacer(1, 10))

        # ================= DONNÉES =================
        data = [[
            "Produit", "Théorique", "Réel",
            "Écart", "%", "Type", "Gravité"
        ]]

        total_pos = total_neg = nb_ecarts = 0

        with sq.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    p.name,
                    s.qty,
                    l.qty_reelle,
                    (l.qty_reelle - s.qty) AS ecart
                FROM inventory_items l
                JOIN products p ON p.ref = l.product_ref
                JOIN stock s ON s.id_libelle = p.ref
                WHERE l.inventory_id = ?
                ORDER BY ABS(ecart) DESC
            """, (inventory_id,))
            rows = cur.fetchall()

        for name, theo, reel, ecart in rows:
            pourcent = (ecart / theo * 100) if theo else 0

            if ecart > 0:
                type_ecart = "Surplus"
            elif ecart < 0:
                type_ecart = "Manquant"
            else:
                type_ecart = "OK"

            if abs(pourcent) < 2:
                gravite = "Faible"
            elif abs(pourcent) < 10:
                gravite = "Moyenne"
            else:
                gravite = "Critique"

            data.append([
                name, theo, reel, ecart,
                f"{pourcent:.1f}%", type_ecart, gravite
            ])

            if ecart != 0:
                nb_ecarts += 1
                if ecart > 0:
                    total_pos += ecart
                else:
                    total_neg += ecart

        # ================= TABLE =================
        table = Table(data, repeatRows=1, colWidths=[
            5*cm, 2*cm, 2*cm, 2*cm, 1.5*cm, 2*cm, 1.5*cm
        ])

        table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#E5E7EB")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("ALIGN", (1,1), (-1,-1), "CENTER"),
            ("BOTTOMPADDING", (0,0), (-1,0), 8),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 12))

        # ================= SYNTHÈSE =================
        elements.append(Paragraph(
            f"""
            <b>Synthèse</b><br/>
            Produits avec écart : {nb_ecarts}<br/>
            Surplus total : {total_pos}<br/>
            Manquant total : {total_neg}
            """,
            styles["Normal"]
        ))

        # ================= PDF =================
        pdf = SimpleDocTemplate(
            fichier_pdf,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        pdf.build(elements)
    def generer_pdf_(self):
        conn = self.cal.connect_to_db(self.db_path)
        if conn is None:
            QMessageBox.critical(self, "Erreur", "Connexion base impossible.")
            return
        try:
            cur = conn.cursor()
            pdf_dir = get_pdf_directory(self, conn)
            if not pdf_dir:
                return

            fichier = os.path.join(pdf_dir, f"rapport_ecarts_inventaire_{self.inventory_id}.pdf")
            infoEntrp = self.cal.print_info(self.db_path)
            if infoEntrp is None:
                return

            self.logo_chemin = self.cal.get_logo_path(cur)
            self.generer_pdf_ecarts(
                fichier_pdf=fichier,
                inventory_id=self.inventory_id,
                db_path=self.db_path,
                logo_path=self.logo_chemin,
                nom_entreprise=infoEntrp["nom"],
            )

            rep = QMessageBox(self)
            rep.setWindowTitle("PDF")
            rep.setText("Facture generee.\nVoulez-vous l'ouvrir maintenant ?")
            btn_yes = rep.addButton("Oui", QMessageBox.ButtonRole.AcceptRole)
            rep.addButton("Non", QMessageBox.ButtonRole.RejectRole)
            rep.exec()
            if rep.clickedButton() == btn_yes:
                self.cal.ouvrir_pdf(fichier)
        except Exception as e:
            QMessageBox.critical(self, "Erreur PDF", str(e))
        finally:
            conn.close()
    # ---------------------------
    # Main Application Snippet
