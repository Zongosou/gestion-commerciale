from logging import log
from operator import index
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,QComboBox,QAbstractItemView,QTableView, 
    QTableWidgetItem, QPushButton, QMessageBox,QTabWidget,QLabel, QDoubleSpinBox,QWidget,QLineEdit
)
from inventaire import AnalyseEcartsDialog
from inventaire.valideInventaire import PopupCorrectionStock, ValidationInventaire
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon,QBrush,QStandardItemModel, QStandardItem
from fonction.methode import Numeroteur, cal
from inventaire.inventDB import DataManageIn
import sqlite3 as sq
# ======================== Saisie d'inventaire ========================
class TabSaisie(QWidget):
    def __init__(self, db_connection, user, parent=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.number_inventory = Numeroteur(db_connection)
        self.inventory_id = self.number_inventory.refe_inventaire()
        self.user = user
        self.cal = cal()
        self.dataSource = DataManageIn(db_connection)
        self.setWindowTitle("Inventaire de stock")
        self.setWindowIcon(QIcon(":/icon/inventaire.png"))
        self.resize(900, 500)
        self._build_ui()
        self.stokage_()
        
    # ---------------- UI ----------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "ID Produit", "Produit", "Qté théorique", "Qté réelle", "Écart", "Commentaires"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        # Boutons
        btns = QHBoxLayout()
        self.label_ = QLabel(f"ID Inventaire:")
        self.label_.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.label_.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.label_ident = QLabel(f"{self.inventory_id}")
        self.label_ident.setStyleSheet("font-weight: bold; font-size: 14px; color: green;")
        self.label_ident.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.label_info = QLabel("Après avoir saisi les quantités réelles,`\n cliquez sur 'Enregistrer en brouillon' pour sauvegarder vos données sans corriger le stock.\n Cliquez sur 'Valider inventaire et corriger le stock' pour finaliser l'inventaire et ajuster les quantités en stock.")
        
        self.btn_save = QPushButton("💾 Enregistrer en brouillon")
        self.btn_validate = QPushButton("✅ Valider inventaire et corriger le stock")
        
        self.btn_save.clicked.connect(self.save_items)
        self.btn_validate.clicked.connect(self.validate_inventory)
        

        btns.addStretch()
        btns.addWidget(self.label_)
        btns.addWidget(self.label_ident)
        btns.addStretch()
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_validate)
        layout.addLayout(btns)
        layout.addWidget(self.label_info)
        
    # ---------------- Data ----------------
    def stokage_(self):
        try:
            df = self.dataSource.get_all_invent()
            if df is None or df.empty:
                QMessageBox.warning(self, "Avertissement", "Aucun produit trouvé dans la base de données.")
                return
            self.table.setRowCount(0)
            self.table.setColumnWidth(0,100)
            self.table.setColumnWidth(1,180)
            self.table.setColumnWidth(2,170)
            self.table.setColumnWidth(3,80)
            self.table.setColumnWidth(4,100)
          
            for index, row in df.iterrows():
                row_p = self.table.rowCount()
                self.table.insertRow(row_p)
                self.doubleSpinbox=QDoubleSpinBox()
                self.doubleSpinbox.setMinimum(0)
                self.doubleSpinbox.setMaximum(9999)
                self.table.setItem(row_p, 0, QTableWidgetItem(str(row["ref"])))                
                self.table.setItem(row_p, 1, QTableWidgetItem(str(row["name"])))
                self.table.setItem(row_p, 2, QTableWidgetItem(str(row["qty"])))
                self.table.setItem(row_p, 3, QTableWidgetItem(str(0)))
                self.table.setCellWidget(row_p,3,self.doubleSpinbox)
                self.table.cellWidget(row_p, 3).valueChanged.connect(lambda: self.cal_ecart())
                self.table.cellWidget(row_p, 3).setValue(0.0)
                self.table.setItem(row_p, 4, QTableWidgetItem(str(0.0)))
                self.table.setItem(row_p, 5, QTableWidgetItem(str("")))
                
        except Exception as e:
            QMessageBox.warning(self,"Erreur",f"{e}")
    
    def cal_ecart(self):
        try:
            msg=''
            self.tab = self.table
            index = self.tab.currentIndex().row()
            the=float(self.tab.item(index,2).text())  
            reel=float(self.tab.cellWidget(index,3).value())    
            ecart=reel - the
            if ecart < 0:
                msg='Perte des données importantes'
            elif ecart == 0:
                msg='Meilleur gestion des données'
            else:
                msg='Bonne gestion des données'
            self.tab.setItem(index,4,QTableWidgetItem(str(ecart))) 
            if ecart < 0:
                self.tab.setItem(index,5,QTableWidgetItem(str(msg)))                 
                self.tab.item(index,5).setBackground(QBrush(QColor('red')))  
            elif ecart == 0:
                self.tab.setItem(index,5,QTableWidgetItem(str(msg)))
                self.tab.item(index,5).setBackground(QBrush(QColor('blue')))  
            else:
                self.tab.setItem(index,5,QTableWidgetItem(str(msg)))
                self.tab.item(index,5).setBackground(QBrush(QColor('green')))  
        except Exception as e:
            log.error(f"Une erreur est survenue: {str(e)}")

   
    def save_items(self):
        donnee = []
        # id,inventory_id, product_ref, qty_theorique, qty_reelle, ecart
        valeur = 0.0
        numero = self.label_ident.text()
        skipped = 0
        conn = self.cal.connect_to_db(self.db_connection)
        if conn is None:
            return
        try:
            cur = conn.cursor()
            for row in range(self.table.rowCount()):
                item_id = (self.table.item(row, 0).text())
                cur.execute("SELECT price_vente FROM stock WHERE id_libelle = ?", (item_id,))
                result = cur.fetchone()
                if not result:
                    skipped += 1
                    continue
                prix_unit = result[0]
                qty_theorique= float(self.table.item(row, 2).text())
                qty_real = float(self.table.cellWidget(row, 3).value())
                ecart = float(self.table.item(row, 4).text())
                valeur += qty_real * float(prix_unit)
                donnee.append([numero,item_id,qty_theorique, qty_real, ecart])
        finally:
            conn.close()
        if not donnee:
            QMessageBox.warning(self, "Inventaire", "Aucune ligne valide a enregistrer.")
            return

        try:
            self.dataSource.save_inventory_with_items(
                numero, self.user, "Inventaire en brouillon", valeur, "BROUILLON", donnee
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Echec enregistrement inventaire: {e}")
            return

        if skipped > 0:
            QMessageBox.information(
                self,
                "Succes",
                f"Inventaire enregistre. {skipped} produit(s) ignore(s) (absents du stock)."
            )
        else:
            QMessageBox.information(self, "Succes", "Inventaire enregistre.")

    def add_inventory(self):
        
        pass
    
    # Corriger les données
    def corrige(self):
        lignes = []
        for row in range(self.table.rowCount()):
            if not self.table.item(row, 0):
                continue
            code = self.table.item(row, 0).text().strip()
            ecart_txt = self.table.item(row, 4).text().strip()
            try:
                ecart = float(ecart_txt)
            except ValueError:
                continue
            if code:
                lignes.append((code, ecart))

        if not lignes:
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("ENREGISTREMENT")
        msg.setText("Etes vous sur de vouloir corriger votre stock initial ?")
        btn_yes = msg.addButton("Oui", QMessageBox.ButtonRole.YesRole)
        msg.addButton("Non", QMessageBox.ButtonRole.NoRole)
        msg.exec()
        if msg.clickedButton() != btn_yes:
            return

        conn = self.cal.connect_to_db(self.db_connection)
        if conn is None:
            return
        try:
            cur = conn.cursor()
            conn.execute("BEGIN IMMEDIATE")
            cmd = '''UPDATE stock SET qty = qty + ? WHERE id_libelle = ?'''
            for code, ecart in lignes:
                cur.execute(cmd, [ecart, code])
            conn.commit()
        except Exception as e:
            conn.rollback()
            log.error(f"Une erreur est survenue: {str(e)}")
            QMessageBox.information(self, "Erreur", f"{e}")
        finally:
            conn.close()

    def validate_inventory(self):
        reply = QMessageBox.question(
            self,
            "Validation",
            "Cette action va corriger le stock.\n"
            "Voulez-vous continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.corrige()
        QMessageBox.information(self, "Succès", "Inventaire validé et stock corrigé ✅")

# ======================== Liste des inventaires ========================
class tableauInventaire(QWidget):
    def __init__(self, db_connection, articles,user=None):
        super().__init__()
        self.articles = articles
        self.db_connection = db_connection
        self.user=user
        self.dataSource = DataManageIn(db_connection)
        
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        # box de liste deroulante
        self.liste_box = QHBoxLayout()
        self.label_liste = QLabel("Liste des inventaires:")
        self.liste_box.addWidget(self.label_liste, alignment=Qt.AlignmentFlag.AlignLeft)
        self.combo_liste = QComboBox()
        self.combo_liste.setPlaceholderText("Sélectionner un inventaire...")
        self.combo_liste.setEditable(False)
        mon_modele = QStandardItemModel()
        self.combo_liste.setModel(mon_modele)
        self.combo_liste.setView(QTableView())
        self.combo = self.combo_liste.view()
        if self.combo:
            self.combo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.combo.setMinimumWidth(400)
            self.combo.setMinimumHeight(150)
            self.combo.setStyleSheet("background-color: white; color: black;")
            self.combo.setSizeAdjustPolicy(QAbstractItemView.SizeAdjustPolicy.AdjustToContents)

        self.liste_box.addWidget(self.combo_liste, stretch= 3)
        self.combo_liste.activated.connect(self.load_inventories)
        layout.addLayout(self.liste_box)
        # box de recherche
        self.box = QHBoxLayout()
        self.label_annee = QLabel("Rechercher:")
        self.box.addWidget(self.label_annee)
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText("Saisir un mot-clé...")
        # self.recherche.textChanged.connect(self.load_inventories)
        self.box.addWidget(self.recherche)
        layout.addLayout(self.box)
        # Table des inventaires
        self.table = QTableWidget(len(articles), 6)
        self.table.setHorizontalHeaderLabels(["ID","ID Inventaire","ID Libelle","Quantité théorie","Quantité réelle","Ecart"])
        self.table.setItem(0, 0, QTableWidgetItem("Liste des produits inventoriés"))
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        self.box_btn = QHBoxLayout()
        
        self.btn_valide = QPushButton("✅ Vailder inventaire (en brouillon)")
        self.btn_valide.setToolTip("Cette action va valider l'inventaire sélectionné en brouillon,sans correction de stock.")
        self.btn_valide.clicked.connect(self.valide_inventaire)
        self.btn_valide_plus_corige = QPushButton("✅ Correction de stock")
        self.btn_valide_plus_corige.setVisible(False)
        self.btn_valide_plus_corige.setToolTip("Cette action va corriger le stock en fonction des quantités inventoriées.")
        self.btn_valide_plus_corige.clicked.connect(self.valide_et_corrige)
        self.btn_analyse_ecart = QPushButton("🔍 Analyser les écarts")
        self.btn_analyse_ecart.clicked.connect(self.analyse_ecarts)
        
        self.box_btn.addWidget(self.btn_valide)
        self.box_btn.addWidget(self.btn_valide_plus_corige)
        self.box_btn.addWidget(self.btn_analyse_ecart)
        layout.addLayout(self.box_btn)
        self.setLayout(layout)
        self.liste_deroulante()
        self.load_inventories()

    def analyse_ecarts(self):
        model = self.combo_liste.model()
        if not model:
            return
        index = self.combo_liste.currentIndex()
        if index < 0:
            return
    
        id_inv = model.index(index, 0).data()
        self.open_dialog = AnalyseEcartsDialog.AnalyseEcartsDialog(self.db_connection,inventory_id=id_inv,parent=self)
        self.open_dialog.show()

    def valide_inventaire(self):
        self.open_dialog = ValidationInventaire(self.db_connection,user=self.user,parent=self)
        self.open_dialog.exec()
        self.liste_deroulante()
        
    def valide_et_corrige(self):
        model = self.combo_liste.model()
        if not model:
            return
        index = self.combo_liste.currentIndex()
        if index < 0:
            return
        staut_corrige= model.index(index, 6).data()
        
        if  staut_corrige == "Oui":
            QMessageBox.information(self, "Erreur", "L'inventaire est déjà corrigé.")
            return
        else:
            id_inv = model.index(index, 0).data()
            self.open_dialog = PopupCorrectionStock(self.db_connection,inventory_id=id_inv,parent=self)
            self.open_dialog.exec()
            self.liste_deroulante()
    # --- Remplir la liste des articles ---
    def liste_deroulante(self):
        """Remplit la liste d'articles."""
        try:
            ligne_donnees = self.dataSource.load_inventories()
            if ligne_donnees is None:
                return
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["ID","Date","User","Statut","Commentaires","Valeur Stock ","Correction Stock"])
            for row in ligne_donnees:
                items = [QStandardItem(str(col)) for col in row]
                
                if row[6] == 1:
                    items[6].setText("Oui")
                else:
                    items[6].setText("Non")
                if row[3] == "Validé & Corrigé":
                    for item in items:
                        item.setBackground(QBrush(QColor('lightblue')))
                if row[3] == "BROUILLON":
                    for item in items:
                        item.setBackground(QBrush(QColor('lightyellow')))
                if row[3] == "Validé":
                    for item in items:
                        item.setBackground(QBrush(QColor('lightgreen')))
                model.appendRow(items)

            self.combo_liste.setModel(model)
        except Exception as e:
            print(f"Erreur lors du chargement de la liste déroulante: {e}")
            log.error("Erreur DB dans liste_deroulante: %s", e)

    def load_inventories(self,index=0):
        # Logique pour charger les inventaires depuis la base de données
        model = self.combo_liste.model()
        if not model or index < 0:
            return

        # lire infos article
        id_inv = model.index(index, 0).data()
       
        inventory = self.dataSource.get_inventory_by_index(index)
        
        if not inventory:
            return
        btn_corriger = self.btn_valide_plus_corige
        # lire infos article
        if inventory[0] == "Validé" and inventory[1] == 0:
            btn_corriger.setVisible(True)
        ligne_donnees = self.dataSource.get_inventory_items(id_inv)
        if ligne_donnees is None:
            return
        self.table.setRowCount(0)
        for row_data in ligne_donnees:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            for col, data in enumerate(row_data):
                self.table.setItem(row_position, col, QTableWidgetItem(str(data)))

class InventoryDialog(QDialog):

    def __init__(self, db_connection, user, parent=None):
        super().__init__(parent)
        self.db_connection = db_connection
        self.user = user
        self.cal = cal()
        self.dataSource = DataManageIn(db_connection)
        self.setWindowTitle("Inventaire de stock")
        self.setWindowIcon(QIcon(":/icon/inventaire.png"))
        self.resize(900, 500)
        self.tableau_saisie = TabSaisie(db_connection, user, parent=None)
        self.tableauInventaire =tableauInventaire(self.db_connection,articles=[],user=self.user)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(self.tableau_saisie, "Saisie Inventaire")
        self.tabs.addTab(self.tableauInventaire, "Liste inventaire")
        self.btn_refresh = QPushButton("🔄 Rafraîchir la liste des inventaires")
        self.btn_refresh.clicked.connect(self.tableauInventaire.liste_deroulante)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(self.btn_refresh)

