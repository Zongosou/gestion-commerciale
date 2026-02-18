from datetime import datetime
import os
from PySide6.QtWidgets import (QWidget,QMessageBox, QVBoxLayout, QLabel, QTableWidget,QHeaderView, 
                               QTableWidgetItem,QHBoxLayout, QDateEdit, QComboBox,
                                 QPushButton)
from PySide6.QtCore import QDate,Qt
from PySide6.QtGui import QIcon 
from caisse.tresorerie_repository import TresorerieRepository
from caisse.tresorie_sercive import RapportManager, TresorerieService
from compta.ecriture import NewTresorerieOp
from fonction.methode import cal
from fonction.model import Model
from piece.compl import get_pdf_directory
from stock.gest_stock import SummaryCard

class SuiviTresorerie(QWidget):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.manager = RapportManager(db_path)
        self.setWindowIcon(QIcon(':/icon/chariot-de-chariot.png'))
        self.setWindowTitle("Suivi de Trésorerie")
        self.resize(900, 520)
        self.service = TresorerieService()
        self.Model = Model()
        self.repo = TresorerieRepository(self.db_path)
        self.cal = cal()
        self.charged = self.cal.charger_configuration_paie()
        charge_devise = self.cal.charger_tva_devise(self.db_path)
        # Configuration par défaut si non trouvée
        self.devise = charge_devise["devise"] if charge_devise else "CFA"
        self.tva = charge_devise["tva"] if charge_devise else "0.0"
        layout = QVBoxLayout(self)
        # ================= CARTES =================
        cards_row = QHBoxLayout()
        self.card_total = SummaryCard("Total des Entrés", "0.0", accent="#2D7EF7")
        self.card_alerts = SummaryCard("Total des Sortis", "0.0", accent="#F59E0B")
        self.card_value = SummaryCard("Solde Final", "0.0", accent="#10B981")

        for card in (self.card_total, self.card_alerts, self.card_value):
            cards_row.addWidget(card, 1)

        layout.addLayout(cards_row)
        # --- Filtres ---
        filter_layout = QHBoxLayout()
        self.btn_ajout = QPushButton("Ajouter Opération")
        self.btn_ajout.setIcon(QIcon(":/icon/caisse-enregistreuse.png"))
        self.btn_ajout.setToolTip("Ajouter une nouvelle opération de trésorerie")
        self.btn_ajout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ajout.setObjectName("PrimaryButton")
        self.btn_ajout.clicked.connect(self.add_operation)
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate.currentDate().addMonths(-1))  # dernier mois par défaut
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QDate.currentDate())
        self.compte_combo = QComboBox()
        self.compte_combo.addItem("Tous les comptes", None)
        self.compte_combo.addItem("Caisse", "Caisse")
        self.compte_combo.addItem("Banque", "Banque")
        self.compte_combo.addItem("Compte Mobile", "Autre")  # tu peux enrichir dynamiquement
        self.btn_apply = QPushButton("Appliquer")
        self.btn_apply.setIcon(QIcon(":/icon/filtre.png"))
        self.btn_apply.setToolTip("Appliquer les filtres")
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.setObjectName("PrimaryButton")
        self.btn_apply.clicked.connect(self.load_filtres)
        filter_layout.addWidget(self.btn_ajout)
        filter_layout.addWidget(QLabel("Du:"))
        filter_layout.addWidget(self.date_from)
        filter_layout.addWidget(QLabel("Au:"))
        filter_layout.addWidget(self.date_to)
        filter_layout.addWidget(QLabel("Compte:"))
        filter_layout.addWidget(self.compte_combo)
        filter_layout.addWidget(self.btn_apply)
        layout.addLayout(filter_layout)
        # --- Tableau ---
        self.table = QTableWidget()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        # --- Label total ---
        self.label_total = QLabel()
        self.label_total.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        layout.addWidget(self.label_total)
        export_layout = QHBoxLayout()
        
        self.btn_export_pdf = QPushButton("Imprimer")
        self.btn_export_pdf.setIcon(QIcon.fromTheme("printer"))
        self.btn_export_pdf.setToolTip("Imprimer le rapport de trésorerie")
        self.btn_export_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_pdf.setObjectName("PrimaryButton")
        self.btn_export_pdf.clicked.connect(self.imprimer_pdf)

        self.refresh_button = QPushButton("Actualiser")
        self.refresh_button.setIcon(QIcon.fromTheme("view-refresh"))
        self.refresh_button.setToolTip("Rafraîchir les données")
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.setObjectName("IconButton")

        self.btn_resume = QPushButton("Résumé Trésorerie")
        self.btn_export_pdf.setIcon(QIcon.fromTheme("view-statistics"))
        self.btn_resume.setToolTip("Voir le résumé de la trésorerie")
        self.btn_resume.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_resume.setObjectName("IconButton")
        self.btn_resume.clicked.connect(self._tab_tresorerie)
        self.refresh_button.clicked.connect(self.refresh)
        

        export_layout.addWidget(self.refresh_button)
        export_layout.addWidget(self.btn_export_pdf)
        export_layout.addWidget(self.btn_resume)
        layout.addLayout(export_layout)
        # Chargement initial
        self.refresh()

    def _update_summary_cards(self, entre, sortis, final):
        # Update labels inside cards
        self.card_total.findChild(QLabel, "SummaryValue").setText(str(entre))
        self.card_alerts.findChild(QLabel, "SummaryValue").setText(str(sortis))
        self.card_value.findChild(QLabel, "SummaryValue").setText(f"{self.cal.separateur_milieur(final)} {self.devise}")


    def load_filtres(self):
        """Recharge le tableau en fonction des filtres"""
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        compte_filter = self.compte_combo.currentData()
        rows = self.repo.get_filtered(date_from=date_from,date_to=date_to,compte=compte_filter)
        # Remplissage tableau + calcul des totaux
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Date", "Libellé", "Type", "Montant", "Compte", "Solde Cumulé"])
        self.table.setRowCount(0)
        solde = 0.0
        total_entrees = 0.0
        total_sorties = 0.0
        for row in rows:
            date, libelle, type_op, montant, compte = row
            montant = float(montant)
            if type_op == "ENTREE":
                solde += montant
                total_entrees += montant
            else:
                solde -= montant
                total_sorties += montant
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(date))
            self.table.setItem(r, 1, QTableWidgetItem(libelle))
            self.table.setItem(r, 2, QTableWidgetItem(type_op))
            self.table.setItem(r, 3, QTableWidgetItem(f"{self.cal.separateur_milieur(montant)} {self.devise}"))
            self.table.setItem(r, 4, QTableWidgetItem(compte))
           
            self.table.setItem(r, 5, QTableWidgetItem(f"{self.cal.separateur_milieur(solde)} {self.devise}"))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # --- Mise à jour du résumé ---
        self._update_summary_cards(
            entre=total_entrees,
            sortis=total_sorties,
            final=solde
        )
        
    def refresh(self):        
        """Recharge le tableau en fonction des filtres"""
        rows = self.manager.recharger_tresorie()
        # Remplissage tableau + calcul des totaux
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Date", "Type", "Libellé", "Montant", "Compte", "Solde Cumulé"])
        self.table.setRowCount(0)
        solde = 0.0
        total_entrees = 0.0
        total_sorties = 0.0
        for row in rows:
            date, type_op, libelle, montant, compte = row
            montant = float(montant)
            type_op = type_op.strip().upper()
            
            if type_op == "ENTREE":
                solde += montant
                total_entrees += montant
            else:
                solde -= montant
                total_sorties += montant

            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(date))
            self.table.setItem(r, 1, QTableWidgetItem(type_op))
            self.table.setItem(r, 2, QTableWidgetItem(libelle))
            self.table.setItem(r, 3, QTableWidgetItem(f"{self.cal.separateur_milieur(montant)} {self.devise}"))
            self.table.setItem(r, 4, QTableWidgetItem(compte))
            # solde_ = f"{solde:,.2f}".replace(","," ").replace(".",",")
            self.table.setItem(r, 5, QTableWidgetItem(f"{self.cal.separateur_milieur(solde)} {self.devise}"))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # --- Mise à jour du résumé ---
        
        self._update_summary_cards(
            entre=total_entrees,
            sortis=total_sorties,
            final=solde
        )
   
   
    def add_operation(self):
        self.op = NewTresorerieOp(self.db_path)
        self.op.exec()   

    def _tab_tresorerie(self):
        resume = self.manager.resume_tresorerie()
        # On passe à 4 colonnes pour inclure le nom du compte
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Compte", "Entrées", "Sorties", "Solde"])
        self.table.setRowCount(len(resume))
        
        for row, (compte, entree, sortie) in enumerate(resume):
            entree = entree or 0.0
            sortie = sortie or 0.0
            solde = entree - sortie
        
            self.table.setItem(row, 0, QTableWidgetItem(str(compte)))
            self.table.setItem(row, 1, QTableWidgetItem(f"{self.cal.separateur_milieur(entree)}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{self.cal.separateur_milieur(sortie)}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{self.cal.separateur_milieur(solde)}"))
            item = QTableWidgetItem(f"{self.cal.separateur_milieur(solde)}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 3, item)
    
    def imprimer_pdf(self):
        from caisse.tresorerie_pdf import TresoreriePDF
        conn = self.cal.connect_to_db(self.db_path)
        if conn is None:
            return
        cur = conn.cursor()
        infoEntrp = self.cal.print_info(self.db_path)
        
        pdf_dir = get_pdf_directory(self, conn)
        if not pdf_dir:
            return
        date_ = datetime.now().strftime("%d_%m_%Y %H_%M_%S")
        pdf_path = os.path.join(pdf_dir, f"rapport_tresorerie_{date_}.pdf")
        if infoEntrp is None:
            return
        self.logo_chemin = self.cal.get_logo_path(cur)
        rows, ent, sor, solde = self.service.calculer_soldes(
            self.repo.get_filtered(
                self.date_from.date().toString("yyyy-MM-dd"),
                self.date_to.date().toString("yyyy-MM-dd"),
                self.compte_combo.currentData()
            )
        )

        pdf = TresoreriePDF(
            entreprise=infoEntrp['nom'],
            logo_path=self.logo_chemin,
            devise=self.devise
        )

        pdf.generer(
            pdf_path,
            rows,
            f"{self.date_from.text()} au {self.date_to.text()}",
            (ent, sor, solde)
        )
        rep = QMessageBox(self)
        
        rep.setWindowTitle("PDF")
        rep.setText("Document généré avec succès.\nVoulez-vous l’ouvrir maintenant ?")

        btn_yes = rep.addButton("Oui", QMessageBox.ButtonRole.AcceptRole)
        btn_no = rep.addButton("Non", QMessageBox.ButtonRole.RejectRole)

        rep.exec()
        if rep.clickedButton() == btn_yes:
            self.cal.ouvrir_pdf(pdf_path)
        else:
            return
                

