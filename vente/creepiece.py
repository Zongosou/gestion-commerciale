# auteur: zongo soumaÃƒÂ¯la
# Tel: +226 54267778 / 70925613
from datetime import datetime
import logging
import locale
import os

from fonction.valide import choixPiece
from piece.compl import get_pdf_directory
locale.setlocale(locale.LC_ALL, "")  # pour sÃƒÂ©parateur milliers si besoin
from fonction.model import Model
from PySide6.QtCore import Qt, QDateTime, QSize
from PySide6.QtWidgets import (
     QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,QApplication,
    QLabel, QLineEdit, QDateTimeEdit, QPushButton, QComboBox, QTableWidget,
    QTableWidgetItem, QDoubleSpinBox, QHeaderView, QMessageBox,QSizePolicy,QDialog,
    QAbstractItemView, QProgressBar, QCompleter, QStyle, QCheckBox, QTableView,
    QInputDialog,QFormLayout
)

from PySide6.QtGui import QIcon, QStandardItemModel, QStandardItem, QAction
from vente.ventDB import DataManage
from fonction.methode import Numeroteur, cal
from vente.vente_service import VenteService
from vente.application.enregistrer_piece import EnregistrerPieceUseCase
from vente.infrastructure.facture_repository import FactureRepository
STATUT_PIECE = {
    "Devis": ["En cours", "Validé"],
    "Commande": ["En cours", "Validé"],
    "Bon de livraison": ["En cours", "Validé"],
    "Facture": ["Brouillon", "Validée"]
}

log = logging.getLogger(__name__)

class Vente(QMainWindow):
    def __init__(self, dbfolder, current_user=None) -> None:
        super().__init__()
        
        self.setWindowIcon(QIcon(':/icon/icone.png'))
        self.dbsource = DataManage(dbfolder)
        self.service = VenteService()
        
        # --- Taille et position fenetre (stable) ---
        screen = QApplication.primaryScreen().availableGeometry()

        # Taille proportionnelle
        self.resize(int(screen.width() * 0.85), int(screen.height() * 0.85))

        # Centrage simple et fiable
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2
        )

        # SizePolicy global pour les éléments extensibles
        sizePolicyExpanding = QSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        sizePolicyTable = QSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.select_ = choixPiece()
        self.select_.pieceChoisie.connect(self.on_piece_selected)

        if self.select_.exec() != QDialog.DialogCode.Accepted:
            self.close()
            return

        self.piece_selected = self.select_.getSelectedPiece()
        if self.piece_selected == "DV":
            self.piece = "Devis"
        elif self.piece_selected == "CM":
            self.piece = "Commande"
        elif self.piece_selected == "BL":
            self.piece = "Bon de livraison"
        elif self.piece_selected == "FAC":
            self.piece = "Facture"
        else:
            QMessageBox.information(self, "Erreur", "Type de pièce invalide.")
            self.close()
            return

        self.dbfolder = dbfolder
        self.conn = cal().connect_to_db(self.dbfolder)
        self.numeroteur = Numeroteur(self.dbfolder)
        self.Model = Model()
        self.cal = cal()
        # Repository
        self.facture_repository = FactureRepository(
            dbsource=self.dbsource,
            numeroteur=self.numeroteur,
            cal=self.cal
        )

        # UseCase
        self.enregistrer_piece_usecase = EnregistrerPieceUseCase(
            repository=self.facture_repository
        )

        central = QWidget(self)
        self.setCentralWidget(central)
        self.setWindowTitle(f"Création de pièce — {self.piece}")
        main = QVBoxLayout(central)
        # --- Informations pièce + client ---
        top_h = QVBoxLayout()
        grp_piece = QGroupBox(f"Réference: {self.piece}")
        grp_piece.setSizePolicy(sizePolicyExpanding)
        
        f1 = QFormLayout()
        self.date_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.num_line = QLineEdit("F-XXXX-YYY")
        self.num_line.setReadOnly(True)
        self.num_line.setStyleSheet("background:#f0f0f0;")

        self.num_line.setEnabled(False)
        self.status_line = QComboBox()
        
        self.date_edit.setSizePolicy(sizePolicyExpanding)
        self.num_line.setSizePolicy(sizePolicyExpanding)
        self.status_line.setSizePolicy(sizePolicyExpanding)
       
        # Info Document
        f1.addRow("Date:",self.date_edit)
        f1.addRow("N°:",self.num_line)
      
        grp_piece.setLayout(f1)

        # Info client
        grp_client = QGroupBox("Client - Remarque")
        grp_client.setSizePolicy(sizePolicyExpanding)
        f2 = QFormLayout()
        self.client_line = QLineEdit()
        self.client_line.setEnabled(False)
        self.client_line.setSizePolicy(sizePolicyExpanding)
        self.remarque_line = QLineEdit()
        self.remarque_line.setSizePolicy(sizePolicyExpanding)
        f2.addRow("Client:",self.client_line)
        f2.addRow("Remarque:",self.remarque_line)
        grp_client.setLayout(f2)

        # Mode de paiement et Statut
        grp_mode = QGroupBox("Mode paiement - Statut pièce")
        f3 = QFormLayout()
        self.mode_paiement = QComboBox()
        f3.addRow("Statut:",self.status_line)
        f3.addRow("Mode de paiement:",self.mode_paiement)
        grp_mode.setLayout(f3)
        # --- Selector article + add button ---
        box_ = QHBoxLayout()

        grp_dis = QGroupBox("Quantitée disponible")
        grp_dis.setMaximumHeight(80)
        box_dis = QFormLayout()
        
        self.label_qty_ = QLabel('0')
        self.label_qty_.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_qty_.setStyleSheet("font-weight: bold; color: green;")
        box_dis.addRow("",self.label_qty_)
        grp_dis.setLayout(box_dis)

        grp_arti = QGroupBox("Articles")
        grp_arti.setMaximumHeight(80)
        add_h = QFormLayout()
        self.article_combo = QComboBox()
        self.article_combo.setEditable(False)
        add_h.addRow("Ajout un article:",self.article_combo)
        grp_arti.setLayout(add_h)
        # add_h.addWidget(label_qty,1 )
        # add_h.addWidget(self.label_qty_,1 )
        box_.addWidget(grp_arti)
        box_.addWidget(grp_dis)
        # --- Panier (table) ---
        grp_panier = QGroupBox("Panier")
        grp_panier.setSizePolicy(sizePolicyTable)
        vpan = QVBoxLayout()

        self.table = QTableWidget(0, 6)
        self.table.setSizePolicy(sizePolicyTable)
        self.table.setStyleSheet("selection-background-color: lightblue;")
        headers = ["Code", "Désignation", "Quantitée", "Prix Unitaire", "Montant", "Action"]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setColumnHidden(0, True)  # ne pas afficher colonne code
        vpan.addWidget(self.table)
        grp_panier.setLayout(vpan)
        

        # --- Paiement / Totaux ---
        bot_h = QHBoxLayout()
        # Left - paiement
        left_g = QGroupBox("Paiement")
        left_g.setMaximumHeight(100)
        left_g.setSizePolicy(sizePolicyExpanding)
        left_l = QHBoxLayout()
        

        self.tva_checkbox = QCheckBox("TVA")
        self.tva_checkbox.setCheckable(True)
        self.tva_spin = QDoubleSpinBox()
        self.tva_spin.setValue(0.0)
        self.tva_spin.setSuffix(" %")
        left_l.addWidget(self.tva_checkbox)
        left_l.addWidget(self.tva_spin)
        left_g.setLayout(left_l)

        # Right - totals & progress
        right_g = QGroupBox("Montants")
        right_g.setMaximumHeight(150)
        right_g.setSizePolicy(sizePolicyExpanding)
        right_l = QVBoxLayout()
        
        row1 = QHBoxLayout()
        self.ht_label = QLabel("0.00")
        self.ht_label.setSizePolicy(sizePolicyExpanding)
        self.ttc_label = QLabel("0.00")
        self.ttc_label.setSizePolicy(sizePolicyExpanding)
        self.paid_spin = QDoubleSpinBox()
        self.paid_spin.setSizePolicy(sizePolicyExpanding)
        self.paid_spin.setMinimum(0.0);self.paid_spin.setMaximum(999999999999); self.paid_spin.setDecimals(2)
        row1.addWidget(QLabel("Montant HT:")); row1.addWidget(self.ht_label,2)
        row1.addWidget(QLabel("Montant TTC:")); row1.addWidget(self.ttc_label,2)
        row1.addWidget(QLabel("Montant versé:")); row1.addWidget(self.paid_spin,2)
        right_l.addLayout(row1)
        # Progress bar and remainder
        self.progress = QProgressBar(); self.progress.setRange(0, 100)
        self.reste_label = QLabel("0.00")
        pb_row = QHBoxLayout()
        pb_row.addWidget(QLabel("Paiement:"),2); pb_row.addWidget(self.progress,2)
        pb_row.addWidget(QLabel("Reste:"),2); pb_row.addWidget(self.reste_label,2)
        right_l.addLayout(pb_row,2)
        right_g.setLayout(right_l)

        bot_h.addWidget(left_g, 3)
        bot_h.addWidget(right_g, 5)

        main.addLayout(box_,0)
        main.addWidget(grp_panier,10)  # TABLE = extensible
        main.addLayout(bot_h,0)     # Totaux FIXES
        # --- Configuration interne ---

        # setup completer/model for article_combo (table-like)
        self.article_model = QStandardItemModel()
        self.article_combo.setModel(self.article_model)

        # n'exÃƒÂ©cute pas exec_() en init Ã¢â‚¬â€ laisse la commande appelante gÃƒÂ©rer l'affichage
        self.current_user = current_user or "Admin"
        self.tau = self.cal.charger_tva_devise(self.dbfolder)
        # --- Liste des articles (table view popup) ---
        mon_modele = QStandardItemModel()
        mon_modele.setHorizontalHeaderLabels(["Désignation", "Code", "Prix Unitaire"])
        mon_modele.setColumnCount(3)
    
        self.article_combo.setModel(mon_modele)
        self.article_combo.setView(QTableView())
        self.combo = self.article_combo.view()
        if self.combo:
            self.combo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.combo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.combo.setMinimumWidth(150)
            self.combo.setMinimumHeight(150)
            self.combo.setStyleSheet("background-color: white; color: black;")
            self.combo.setSizeAdjustPolicy(QAbstractItemView.SizeAdjustPolicy.AdjustToContents)

        # --- champs internes ---
        self.libelle = None
        self.code = None
        self.prix = None
        self.reste = 0.0
        self.net = 0.0
        self.id_clt = None
        self.nom_clt = None

        # --- config + init ---
        self.populate_accounts_combos()
        self.mette_a_jour(piece=self.piece)
        
        self.choix_()

        # autocomplete remarques
        data_list = self.dbsource.get_data_remaeque() or []
        completer = QCompleter(data_list)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.remarque_line.setCompleter(completer)

        # --- connexions ---
      
        self.tva_spin.valueChanged.connect(self.mnt_ttc)
        self.paid_spin.valueChanged.connect(self.mnt_ttc)
        self.date_edit.setDateTime(QDateTime.currentDateTime())
        self.article_combo.activated.connect(lambda index: self.combo_article_selected(index))
        self.mode_paiement.activated.connect(lambda: self.type_paiement())
        self.tva_checkbox.stateChanged.connect(lambda: self.validateSelection())

        # charger articles pour dÃƒÂ©pÃƒÂ´t par dÃƒÂ©faut
        self.liste_deroulante()

        tb = self.addToolBar("Actions")
        tb.setStyleSheet("background-color: #f0f0f0;")
        tb.setObjectName("MainToolbar")
        tb.setMovable(False)
        tb.setIconSize(QSize(24, 24))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        act_validate = QAction(QIcon.fromTheme("document-save", self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)), "Valider", self)
        act_print = QAction(QIcon.fromTheme("document-print", self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)), "Imprimer", self)
        act_new = QAction(QIcon.fromTheme("list-add", self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder)), "Nouvelle pièce", self)
        act_client =  QAction(QIcon(":/icon/300.png"), "Sélection du client", self)
       
        tb.addAction(act_client)
        tb.addAction(act_validate)
        tb.addAction(act_print)
        tb.addAction(act_new)
        tb.addSeparator()
        tb.addWidget(grp_client)
        tb.addSeparator()
        tb.addWidget(grp_piece)
        tb.addSeparator()
        tb.addWidget(grp_mode)
        
        
        act_client.triggered.connect(lambda: self.id_client())
        act_validate.triggered.connect(lambda: self.list_vente())
        act_new.triggered.connect(lambda: self.open_window())  
        act_print.triggered.connect(lambda: self.facture_generate())
        if self.piece != "Facture":
            self.mode_paiement.setEnabled(False)
            self.paid_spin.setEnabled(False)

    def open_window(self):
        Vente(self.dbfolder, current_user=self.current_user).show()

    def _apply_styles(self):
        with open("config/style.qss", "r", encoding="utf-8") as f:
            style = f.read()
            self.setStyleSheet(style)
# ===============================
# --- SI UNE PIECE EST SELECTIONNEE ---
# ===============================
    def on_piece_selected(self, piece_code: str):
        self.piece = piece_code
# ===============================
# --- TYPE DE PAIEMENT ---
# ===============================
    def type_paiement(self):
        moyen = self.dbsource.cal.code_paiement(self.mode_paiement.currentText())
        moyen_ = f"{moyen}-{self.num_line.text()}"
        return moyen_

    # Afficher et selectionner un client
    def id_client(self):

        row = self.dbsource.get_liste_client()
        liste_clients = [f"{id_}_{nom}" for id_,nom in row]
        dialog = QInputDialog(self)
        dialog.setWindowTitle("Sélectionner un client")
        dialog.setLabelText("CLIENTS")
        dialog.setComboBoxItems(liste_clients)
        # Texte des boutons
        dialog.setOkButtonText("Sélectionner")
        dialog.setCancelButtonText("Annuler")

        # Ã¢Å“â€¦ Taille personnalisÃ©e
        dialog.resize(500, 350)   # largeur, hauteur

        # Optionnel : largeur minimale
        dialog.setMinimumWidth(450)

        if dialog.exec():
            select_client = dialog.textValue()
            self.id_clt, self.nom_clt = select_client.split("_", 1)
            self.client_line.setText(self.nom_clt)

    # --- Remplir la liste des articles ---
    def liste_deroulante(self):
        """Remplit la liste d'articles."""
        try:
            rows = self.dbsource.get_liste_produit()
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["Prod", "Code", "Prix Unitaire"])
            for row in rows:
                items = [QStandardItem(str(col)) for col in row]
                model.appendRow(items)
            self.article_combo.setModel(model)
        except Exception as e:
            log.error("Erreur DB dans liste_deroulante: %s", e)

    # --- RÃƒÂ©cupÃƒÂ©rer les remarques existantes ---
    

    def get_statut(self, piece: str):
        return STATUT_PIECE.get(piece, [])

    def mette_a_jour(self, piece):
        self.status_line.clear()
        self.status_line.addItems(self.get_statut(piece))

    # --- Choix de la piÃ¨ce et Numetation fictive ---
    def choix_(self):
        text_ = self.piece
        if text_ == "Devis":
            self.num_line.setText(str(self.numeroteur.preview("DV")))
            
        elif text_ == "Commande":
            self.num_line.setText(str(self.numeroteur.preview("CMD")))
        elif text_ == "Bon de livraison":
            self.num_line.setText(str(self.numeroteur.preview("BL")))
        elif text_ == "Facture":
            self.num_line.setText(str(self.numeroteur.preview("FAC")))
        else:
            QMessageBox.information(self, "Document", "Option inconnue")
# ===============================
# --- VALIDATION DE LA SÃƒâ€°LECTION ---
# ===============================
    def validateSelection(self):
        if self.tva_checkbox.isChecked():
            if self.tau:
                self.tva_spin.setValue(float(self.tau.get('tva', 0)))
            self.tva_spin.setEnabled(True)
        else:
            self.tva_spin.setEnabled(False)
            self.tva_spin.setValue(0)

# ===============================
# --- LIESTE DES ARTICLES ---
# ===============================
    def combo_article_selected(self, index):
        """Ajoute l'article sélectionne dans la table si stock dispo."""
        try:

            model = self.article_combo.model()
            if not model or index < 0:
                return

            # lire infos article
            libelle = model.index(index, 0).data()
            code = model.index(index, 1).data()
            prix = float(model.index(index, 2).data())

            quantite_depot_raw = self.dbsource.get_stock_dispo(code)
            try:
                quantite_depot = float(quantite_depot_raw or 0)
            except (TypeError, ValueError):
                quantite_depot = 0.0

            self.label_qty_.setText(str(quantite_depot_raw))

            piece_code = str(self.piece).strip().upper()
            is_facture = piece_code in ("FACTURE", "FAC")

            # vÃƒÂ©rifier stock dispo avant ajout (uniquement pour facture)
            if is_facture:
                if quantite_depot < 1:
                    QMessageBox.warning(
                        self,
                        "Stock insuffisant",
                        f"L'article '{libelle}' (code {code}) n'a pas de stock.\n"
                        f"Stock disponible : {quantite_depot} unité(s)."
                    )
                    return
                
                if self.cal.verifi_exit(self.table, code) is False:

                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    qt_spin = QDoubleSpinBox()
                    qt_spin.setMinimum(0)
                    qt_spin.setMaximum(9999999999)
                    qt_spin.setValue(1.0)
                    qt_spin.valueChanged.connect(self.upd_value_cel)
                    prix_spin = QDoubleSpinBox()
                    prix_spin.setMinimum(0)
                    prix_spin.setMaximum(9999999999)
                    prix_spin.setValue(prix)
                    prix_spin.valueChanged.connect(self.upd_value_cel)
                    montant = 1 * prix
                    # bouton supprimer (liÃƒÂ© ÃƒÂ  la ligne)
                    btn = QPushButton("Supprimer")
                    btn.setStyleSheet("background-color: transparent;border: none; color: red;")
                    btn.clicked.connect(lambda _, r=row: self.remove_row(r))
                    # remplir ligne
                    self.table.setItem(row, 0, QTableWidgetItem(code))
                    self.table.setItem(row, 1, QTableWidgetItem(libelle))
                    self.table.setCellWidget(row, 2, qt_spin)
                    self.table.setCellWidget(row, 3, prix_spin)
                    self.table.setItem(row, 4, QTableWidgetItem(f"{montant:.2f}"))
                    self.table.setCellWidget(row, 5, btn)
                    self.somme_vente()
                else:
                    QMessageBox.information(self, "Ajout article", f"L'article :'{libelle}' existe déjà  dans la liste.")
            else:
                if self.cal.verifi_exit(self.table, code) is False:

                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    qt_spin = QDoubleSpinBox()
                    qt_spin.setMinimum(0)
                    qt_spin.setMaximum(9999999999)
                    qt_spin.setValue(1.0)
                    qt_spin.valueChanged.connect(self.upd_value_cel)
                    prix_spin = QDoubleSpinBox()
                    prix_spin.setMinimum(0)
                    prix_spin.setMaximum(9999999999)
                    prix_spin.setValue(prix)
                    prix_spin.valueChanged.connect(self.upd_value_cel)
                    montant = 1 * prix
                    # bouton supprimer (liÃƒÂ© ÃƒÂ  la ligne)
                    
                    btn = QPushButton("Supprimer")
                    btn.setStyleSheet("background-color: transparent;border: none; color: red;")
                    btn.clicked.connect(lambda _, r=row: self.remove_row(r))
                    # remplir ligne
                    self.table.setItem(row, 0, QTableWidgetItem(code))
                    self.table.setItem(row, 1, QTableWidgetItem(libelle))
                    self.table.setCellWidget(row, 2, qt_spin)
                    self.table.setCellWidget(row, 3, prix_spin)
                    self.table.setItem(row, 4, QTableWidgetItem(f"{montant:.2f}"))
                    self.table.setCellWidget(row, 5, btn)
                    self.somme_vente()
                else:
                    QMessageBox.information(self, "Ajout article", f"L'article :'{libelle}' existe déjà  dans la liste.")

        except Exception as e:
            log.error("Erreur combo_article_selected: %s", e)
            QMessageBox.critical(self, "Erreur", f"Impossible d'ajouter l'article.\n{e}")



# ===============================
# --- RETIRER UNE LIGNE ---
# ===============================

    def remove_row(self, row_index: int):
        try:
            if row_index < 0 or row_index >= self.table.rowCount():
                QMessageBox.warning(self, 'Avertissement', 'Ligne invalide.')
                return
            msg = QMessageBox(self)
            msg.setWindowTitle("SUPPRESSION")
            msg.setText("Etes-vous sur de vouloir retirer cette ligne ?")
            yes = msg.addButton("Oui", QMessageBox.ButtonRole.YesRole)
            non = msg.addButton("Non", QMessageBox.ButtonRole.NoRole)
            msg.exec()
            if msg.clickedButton() == yes:
                self.table.removeRow(row_index)
                self.somme_vente()
        except Exception as e:
            log.error(f"Erreur remove_row: {e}")

    
# ===============================
# --- MISE Ãƒâ‚¬ JOUR DES VALEURS ---
# ===============================
    def upd_value_cel(self):
        try:
            index = self.table.currentIndex().row()
            if index < 0:
                # Si pas de ligne sÃ©lectionnÃ©e on recalculera tous les montants
                pass
            # recalculer le montant de la ligne courante (ou de toutes)
            
            for row in range(self.table.rowCount()):
                prix_widget = self.table.cellWidget(row, 3)
                qte_widget = self.table.cellWidget(row, 2)
                if prix_widget is None or qte_widget is None:
                    continue
                
                prix = float(prix_widget.value())
                qte = float(qte_widget.value())
                new_mnt = prix * qte
                self.table.setItem(row, 4, QTableWidgetItem(f"{new_mnt:.2f}"))

            # recalcul total
            total_sum = 0.0
            for row in range(self.table.rowCount()):
                mnt_item = self.table.item(row, 4)
                if mnt_item:
                    try:
                        total_sum += float(mnt_item.text())
                    except ValueError:
                        continue
            self.ht_label.setText(f"{total_sum:.2f}")
            self.somme_vente()
        except Exception as e:
            log.error(f"upd_value_cel error: {e}")

# ===============================
# --- CALCUL DU TOTAL DE LA VENTE ---
# ===============================
    def somme_vente(self):
        total_sum = 0.0
        for row in range(self.table.rowCount()):
            mnt = self.table.item(row, 4)
            if mnt is not None:
                try:
                    total_sum += float(mnt.text())
                except ValueError:
                    log.warning(f"Valeur non numerique dans le montant de la ligne {row}:{mnt.text()}")
                    continue
        self.ht_label.setText(f"{total_sum:.2f}")
        self.mnt_ttc()

# ===============================
# --- CALCUL DU MONTANT TTC ---
# ===============================

    def mnt_ttc(self):
        try:
            mnt_ht = float(self.ht_label.text()) if self.ht_label.text() else 0.0
        except ValueError:
            mnt_ht = 0.0
        va_aj = self.tva_spin.value()
        e_mntpy = self.paid_spin.value()
        net = self.service.calcul_ttc(mnt_ht, va_aj)
        reste = self.service.calcul_reste(net, e_mntpy)

        # formatage
        self.ttc_label.setText(f"{net:.2f}")
        self.reste_label.setText(f"{reste:.2f}")

        # progression paiement en pourcentage
        percent = 0
        if net > 0:
            percent = int(min(max((e_mntpy / net) * 100, 0), 100))
        self.progress.setValue(percent)
        
# ===============================
# --- COMBOBOX DES MOYENS DE PAIEMENT ---
# ===============================

    def populate_accounts_combos(self):
        """Remplit les status_line des comptes des la base de données."""
        fichier_json = self.cal.load_json()
        try:
            self.mode_paiement.clear()
            # garder 1ÃƒÂ¨re option neutre
            self.mode_paiement.addItem("Moyen de paiement", None)
            for num in fichier_json:
                libelle = num.get("libelle")
                compte = num.get("compte")
                self.mode_paiement.addItem(libelle, compte)
        except Exception as e:
            QMessageBox.critical(self, "Erreur SQL", f"Erreur lors du chargement des moyen de paiement: {e}")


# ===============================
# --- VALIDATION DES SAISIES ---
# ===============================
    def _validate_inputs(self) -> bool:
        """Vérifie que toutes les conditions de saisie sont remplies"""
        nmclt = self.nom_clt

        if self.table.rowCount() <= 0:
            QMessageBox.warning(self, "ENREGISTREMENT", "Aucun article. Veuillez ajouter des produits !")
            return False
        if not self.piece or self.piece == "Pièces":
            QMessageBox.warning(self, "ENREGISTREMENT", "Type de pièce non reconnu.")
            return False
        if nmclt == "" or None:
            QMessageBox.warning(self, "ENREGISTREMENT", "Veuillez sélectionner un client.")
            return False
        return True

    
    @staticmethod
    def safe_execution(func):
        """Décorateur pour capturer les erreurs et afficher un QMessageBox"""
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                log.exception("Erreur: %s", e)
                QMessageBox.critical(self, "Erreur", f"Une erreur est survenue : {e}")
                return None
        return wrapper

# ===============================
# --- ENREGISTREMENT DES VENTES ---
# ===============================
    @safe_execution
    def list_vente(self):
        """Enregistre les donnees de vente avec l'utilisateur courant"""

        conn = self.cal.connect_to_db(self.dbfolder)

        if conn is None:
            QMessageBox.critical(self, "Erreur BD", "Impossible de se connecter à la base de données.")
            return

        cur = conn.cursor()

        PIECES = {
            "Facture": "FAC",
            "Bon de livraison": "BL",
            "Commande": "CMD",
            "Devis": "DV"
        }

        prefixe = PIECES[self.piece]
        numero = self.numeroteur.generer(prefixe, conn=conn, cur=cur)

        conn.commit()

        if numero is None:
            raise RuntimeError("Impossible de générer un numéro de pièce.")

        self.num_line.setText(numero)
        conn.close()

        # 🔥 LOGIQUE STATUT AUTOMATIQUE
        etat_piece_ = self.service.statut_paiement(
            type_piece=self.piece, 
            statut_piece =self.status_line.currentText(),
            net= float(self.ttc_label.text() or 0),
            verse=self.paid_spin.value()
            )
        

        self.enregistrer_piece_usecase.execute(
            piece=self.piece,
            id_clt=self.id_clt,
            nom_clt=self.nom_clt,
            table_widget=self.table,
            date_edit=self.date_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            numero=numero,
            montant_ht=float(self.ht_label.text()),
            montant_verse=self.paid_spin.value(),
            tva=self.tva_spin.value(),
            remarque=self.remarque_line.text(),
            current_user=self.current_user,
            etat_piece=self.status_line.currentText(),
            etat_paiement = etat_piece_,
            mode_paiement=self.mode_paiement.currentText()
        )

        QMessageBox.information(
            self,
            "Succès",
            f"{self.piece} enregistré(e) en {etat_piece_} : {numero}"
        )


        # except Exception as e:
        #     QMessageBox.critical(self, "Erreur", str(e))

    # def list_vente(self):
    #     """Enregistre les donnees de vente avec l'utilisateur courant"""
    #     if not self._validate_inputs():
    #         return

    #     PIECES = {
    #         "Facture": "FAC",
    #         "Bon de livraison": "BL",
    #         "Commande": "CMD",
    #         "Devis": "DV"
    #     }

    #     if self.piece not in PIECES:
    #         QMessageBox.warning(self, "Erreur", "Type de piÃ¨ce inconnu")
    #         return

    #     conn = self.cal.connect_to_db(self.dbfolder)
    #     dat = self.date_edit.dateTime().toString("yyyy-MM-dd HH:mm")
    #     dat_ = datetime.strptime(dat, "%Y-%m-%d %H:%M").date()
    #     taut_tva = self.tva_spin.value()
    #     montant_ht = float(self.ht_label.text() or 0)

    #     if conn is None:
    #         QMessageBox.critical(self, "Erreur BD", "Impossible de se connecter Ã  la base de donnÃ©es.")
    #         return

    #     if self.piece == "Facture":
    #         etat_piece = self.service.statut(
    #             float(self.ttc_label.text() or 0),
    #             self.paid_spin.value()
    #         )
    #     else:
    #         etat_piece = self.status_line.currentText()

    #     try:
    #         cur = conn.cursor()
    #         conn.execute("BEGIN IMMEDIATE")

    #         prefixe = PIECES[self.piece]
    #         numero = self.numeroteur.generer(prefixe, conn=conn, cur=cur)
    #         if numero is None:
    #             raise RuntimeError("Impossible de gÃ©nÃ©rer un numÃ©ro de piÃ¨ce.")
    #         self.num_line.setText(numero)

    #         L = self.service.Liste_donne(
    #             id_clt=self.id_clt,
    #             factu=numero,
    #             dat=dat_,
    #             remarque=self.remarque_line.text(),
    #             date_edit=self.date_edit,
    #             mnt_ht=montant_ht,
    #             e_mntpy=self.paid_spin.value(),
    #             va_aj=taut_tva,
    #             piece=self.piece,
    #             current_user=self.current_user,
    #             etat=etat_piece
    #         )

    #         data_vente = self.dbsource.get_data_by(
    #             self.id_clt,
    #             self.nom_clt,
    #             self.table,
    #             self.date_edit,
    #             numero
    #         )

    #         if not data_vente:
    #             conn.rollback()
    #             QMessageBox.warning(self, "DonnÃ©es manquantes", "Aucune ligne de vente trouvÃ©e.")
    #             return

    #         if self.piece == "Facture":
    #             self.dbsource._save_facture(
    #                 cur,
    #                 mode_paiement=self.mode_paiement.currentText(),
    #                 L=L,
    #                 data_vente=data_vente,
    #                 numero=numero,
    #                 date_emission=self.date_edit.dateTime().toString("yyyy-MM-dd HH:mm"),
    #                 user=self.current_user
    #             )
    #         else:
    #             self.dbsource._save_devis_commande(cur, L, data_vente)

    #         conn.commit()
    #     except Exception as e:
    #         conn.rollback()
    #         QMessageBox.critical(self, "Erreur", f"Ã‰chec de l'enregistrement : {e}")
    #         return
    #     finally:
    #         conn.close()

    #     QMessageBox.information(self, "Succes", f"{self.piece} : {self.num_line.text()} enregistree par {self.current_user}.")

# ===============================
# --- LISTE DES ARTICLES POUR ENREGISTREMENT ---
# ===============================
    def liste_article(self):
        
        table = self.table
        donnee = []
        for row in range(table.rowCount()):
            if not table.item(row, 0):
                continue

            code_item = table.item(row, 0)
            if code_item is None:
                continue
            code = code_item.text()
            prd_item = table.item(row, 1)
            if prd_item is None:
                continue
            prd = prd_item.text()
            qte = float(table.cellWidget(row, 2).value())
            pri = float(table.cellWidget(row, 3).value())
            mnt_item = table.item(row, 4)
            mnt = float(mnt_item.text()) if mnt_item is not None else pri * qte
            row_data = [prd,qte, pri, mnt]
            donnee.append(row_data)

        return donnee
    
# ===============================
# --- GENERATION DE LA DOCUMENT ---
# ===============================
    def facture_generate(self):
        try:
            facture_num = self.num_line.text()
            date = self.date_edit.date().toString("dd/MM/yyyy")
            conn = self.cal.connect_to_db(self.dbfolder)
            tva = self.tva_spin.value()
            remarque = self.remarque_line.text()
            total_ht = float(self.ht_label.text())
            total_ttc = (total_ht * tva / 100)
            net = total_ht + total_ttc

            verse = self.paid_spin.value()
            reste = total_ttc - verse
            if conn is None:
                return
            cur = conn.cursor()
            vente = self.dbsource.get_client_by_id(id_clt=self.id_clt,date=date,facto=facture_num,tva=tva,montant_verse=verse,reste=reste,type_fact=self.piece,remarque=remarque)
            if not vente:
                return
            infoEntrp = self.cal.print_info(self.dbfolder)
            self.tau = self.cal.charger_tva_devise(self.dbfolder)
            if self.tau is None:
                return
            if infoEntrp is None:
                return
            donne = self.liste_article()
            self.logo_chemin = self.cal.get_logo_path(cur)
            self.sig_chemin = self.cal.get_sign_path(cur)
            self.cah_chemin = self.cal.get_cach_path(cur)
            donnees = self.Model.facture_donnees(
                Entr=infoEntrp['nom'],
                T1=infoEntrp['T1'],
                T2=infoEntrp['T2'],
                info=infoEntrp['info'],
                ville=infoEntrp['ville'],
                adresse=infoEntrp['adresse'],
                responsabable=infoEntrp['resp'],
                ifu=infoEntrp['ifu'],
                autre=infoEntrp['autre'],
                list_article=donne,
                vente=vente,
                msg=vente["type_facture"],
                remarque=remarque,
                date=datetime.now().strftime("%d/%m/%Y"),
                chemin=self.logo_chemin,
                sign=self.sig_chemin,
                cahet=self.cah_chemin,
                taux=self.tau.get('tva', 0),
                devise=self.tau.get('devise','')

            )

            pdf_dir = get_pdf_directory(self, conn)
            if not pdf_dir:
                return

            facture_numero = vente['facture']
            pdf_path = os.path.join(pdf_dir, f"{facture_numero}.pdf")
           
            self.Model.generer_facture_pdf_reportlab(donnees, pdf_path)
            rep = QMessageBox(self)
            rep.setWindowTitle("PDF")
            rep.setText(f"{self.piece} {facture_numero} généré(e).\nVoulez-vous l'ouvrir maintenant ?")

            btn_yes = rep.addButton("Oui", QMessageBox.ButtonRole.AcceptRole)
            btn_no = rep.addButton("Non", QMessageBox.ButtonRole.RejectRole)

            rep.exec()
            if rep.clickedButton() == btn_yes:
                self.cal.ouvrir_pdf(pdf_path)
            else:
                return
                
        except Exception as e:
            log.error(e, exc_info=True)
            QMessageBox.critical(self, "Erreur PDF", str(e))
        finally:
            if conn:
                conn.close()

    # --- fin de la classe VentePiece ---

