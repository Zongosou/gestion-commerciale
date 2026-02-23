from datetime import datetime
import os
from PySide6.QtWidgets import (QToolBar, QWidget,QMessageBox, QVBoxLayout, QLabel, QTableWidget,QHeaderView, 
                               QTableWidgetItem,QHBoxLayout, QDateEdit, QComboBox,
                                 QPushButton)
from PySide6.QtCore import QDate, QSize,Qt
from PySide6.QtGui import QAction, QIcon 
from caisse.tresorerie_repository import TresorerieRepository
from caisse.tresorie_sercive import RapportManager, TresorerieService
from compta.ecriture import NewTresorerieOp
from fonction.methode import cal
from fonction.model import Model
from piece.compl import get_pdf_directory
from stock.gest_stock import SummaryCard

class SuiviTresorerie(QWidget):
    def __init__(self, db_path,user=None):
        super().__init__()
        self.db_path = db_path
        self.user = user
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
        self.toolbar_actions = self.create_toolbar_actions()
        self.toolbar_actions.setIconSize(QSize(24, 24))
        self.toolbar_actions.setMovable(False)
        layout.addWidget(self.toolbar_actions)
        # --- Filtres ---
        filter_layout = QHBoxLayout()
        
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
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        # self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        # --- Label total ---
        self.label_total = QLabel()
        self.label_total.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        layout.addWidget(self.label_total)
        
        
        # Chargement initial
        self.refresh()
    
    def create_toolbar_actions(self):
        toolbar = QToolBar("Actions Trésorerie", self)
        # toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        act_ajout = QAction(QIcon(),"Ajouter",self)
        act_ajout.triggered.connect(self.add_operation)

        act_refresh = QAction(QIcon(), "Actualiser", self)
        act_refresh.triggered.connect(self.refresh)

        act_print = QAction(QIcon(), "Imprimer", self)
        act_print.triggered.connect(self.imprimer_pdf)

        act_resume = QAction(QIcon(), "Résumé", self)
        act_resume.triggered.connect(self._tab_tresorerie)

        toolbar.addAction(act_ajout)
        toolbar.addSeparator()
        toolbar.addAction(act_print)
        toolbar.addSeparator()
        toolbar.addAction(act_resume)
        toolbar.addSeparator()
        toolbar.addAction(act_refresh)

        return toolbar

    def _update_summary_cards(self, entre, sortis, final):
        # Update labels inside cards
        self.card_total.findChild(QLabel, "SummaryValue").setText(f"{self.cal.separateur_milieur(entre)} {self.devise}")
        self.card_alerts.findChild(QLabel, "SummaryValue").setText(f"{self.cal.separateur_milieur(sortis)} {self.devise}")
        self.card_value.findChild(QLabel, "SummaryValue").setText(f"{self.cal.separateur_milieur(final)} {self.devise}")


    
    def _load_data(self, rows):
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Type", "Libellé", "Montant", "Compte", "Solde Cumulé"]
        )
        self.table.setRowCount(0)

        solde = 0.0
        total_entrees = 0.0
        total_sorties = 0.0

        for row_data in rows:
            date, type_op, libelle, montant, compte = row_data
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

            # Montant tri numérique réel
            montant_item = QTableWidgetItem()
            montant_item.setData(Qt.ItemDataRole.DisplayRole, montant)
            montant_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            self.table.setItem(r, 3, montant_item)

            self.table.setItem(r, 4, QTableWidgetItem(compte))

            solde_item = QTableWidgetItem()
            solde_item.setData(Qt.ItemDataRole.DisplayRole, solde)
            solde_item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
            self.table.setItem(r, 5, solde_item)

            # 🎨 Couleurs professionnelles
            if type_op == "ENTREE":
                self.table.item(r, 1).setForeground(Qt.GlobalColor.darkGreen)
            else:
                self.table.item(r, 1).setForeground(Qt.GlobalColor.red)

            if solde < 0:
                self.table.item(r, 5).setForeground(Qt.GlobalColor.red)

        self._update_summary_cards(total_entrees, total_sorties, solde)
    
    def load_filtres(self):
        rows = self.repo.get_filtered(
            self.date_from.date().toString("yyyy-MM-dd"),
            self.date_to.date().toString("yyyy-MM-dd"),
            self.compte_combo.currentData()
        )
        self._load_data(rows)
        
    def refresh(self):
        rows = self.manager.recharger_tresorie()
        self._load_data(rows)
   
    def add_operation(self):
        op = NewTresorerieOp(self.db_path, self.user)
        if op.exec():
            self.refresh()  

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
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.DisplayRole, solde)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
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
                

