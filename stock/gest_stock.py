from PySide6.QtWidgets import (
     QHeaderView, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QFrame, QDialog,
    QMessageBox,QToolBar,QSizePolicy,QLineEdit
)
from PySide6.QtGui import QColor, QIcon,QAction
from PySide6.QtCore import Qt 
from  fonction.methode import cal
from stock.add_product_dialog import AddProductDialog
from stock.edit_product_dialog import EditProductDialog
from stock.paiement_four import SupplierPaymentDialog
from stock.stock_db import DataManage
from stock.load_hist import GestHistStock
from inventaire.InventoryDialog import InventoryDialog
import os
from stock.add_piece import AchatModule
class SummaryCard(QFrame):
    def __init__(self, title: str, value: str, accent: str = "#2D7EF7", parent=None):
        super().__init__(parent)
        self.setObjectName("SummaryCard")

        self.setMinimumHeight(70)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        # ================= CONTENU =================
        content = QWidget()
        content_layout = QVBoxLayout(content)

        title_label = QLabel(title)
        value_label = QLabel(value)

        title_label.setObjectName("SummaryTitle")
        value_label.setObjectName("SummaryValue")

        content_layout.addWidget(title_label)
        content_layout.addWidget(value_label)
        content_layout.setContentsMargins(8, 6, 8, 8)

        # ================= BARRE ACCENT =================
        accent_bar = QFrame()
        accent_bar.setFixedWidth(2)
        accent_bar.setStyleSheet(
            f"background-color: {accent}; border-radius: 2px;"
        )

        # ================= LAYOUT PRINCIPAL =================
        main_layout = QHBoxLayout(self)   # ✅ UN SEUL layout sur self
        main_layout.addWidget(accent_bar)
        main_layout.addWidget(content)
        main_layout.setContentsMargins(0, 0, 0, 0)


class StockApp(QWidget):
    def __init__(self,  db_connection, user):
        super().__init__()
        self.user = user
        self.db_connection = db_connection
        self.cal = cal()
        self.dataSource = DataManage(db_connection)
    # ---------------------------
        self.create_actions()
        toolbar = self.create_toolbar()
        
        
    # UI Builders
        container = QWidget()
        container.setObjectName("StockContainer")
        layout_ = QVBoxLayout(container)
        layout_.setContentsMargins(0, 0, 0, 0)
        layout_.setSpacing(2)
        layout_.addWidget(toolbar)

        # Summary cards
        cards_row = QHBoxLayout()
        self.card_total = SummaryCard("Nombre total de produits", "0", accent="#2D7EF7")
        self.card_alerts = SummaryCard("Alertes stock faible", "0", accent="#F59E0B")
        self.card_value = SummaryCard("Valeur totale du stock", "0.0", accent="#10B981")
        self.card_marge = SummaryCard("Marge potentielle", "0.0", accent="#F97316")

        cards_row.addWidget(self.card_total)
        cards_row.addWidget(self.card_alerts)
        cards_row.addWidget(self.card_value)
        cards_row.addWidget(self.card_marge)
        layout_.addLayout(cards_row)
        # Table
        table_container = QFrame()
        table_container.setObjectName("TableContainer")
        # Box recherche 
        rech_box = QHBoxLayout()
        lab_reche_titre = QLabel("Rechercher:")
        text_input = QLineEdit()
        text_input.setPlaceholderText("Refe, nom, catég.....")
        text_input.textChanged.connect(self.filter_table)
        rech_box.addWidget(lab_reche_titre)
        rech_box.addWidget(text_input)
        layout_.addLayout(rech_box)

        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Reference","Nom", "Catégorie", "Quantité", "Prix achat","Prix vente", "Statut"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setShowGrid(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemDoubleClicked.connect(lambda _: self.open_edit_product_dialog())
        box_btn_h = QHBoxLayout()
        self.btn_hist_achat = QPushButton("Historique des Entrés.")
        self.btn_hist_achat.setIcon(QIcon(':/icon/historique.png'))
        self.btn_hist_achat.setObjectName("IconButton")
        self.btn_hist_achat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hist_achat.setToolTip("Voir l'historique des achats")
        self.btn_hist_achat.clicked.connect(self.open_hist_achat)

        box_btn_h.addWidget(self.btn_hist_achat)
        pay_btn = QPushButton("Paiement Fournisseur")
        pay_btn.setObjectName("IconButton")
        pay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pay_btn.clicked.connect(self.open_supplier_payment)
        pay_btn.setToolTip("Effectuer le paiement d'un fournisseur")
        box_btn_h.addWidget(pay_btn)

        table_layout.addWidget(self.table)
        table_layout.addLayout(box_btn_h)
        
        layout_.addWidget(table_container, 1)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(container)
        
        data = self.dataSource.get_all_products()
        self._populate_table(data)
        self._update_summary_cards(data)

    def open_supplier_payment(self):
        dialog = SupplierPaymentDialog(self.db_connection,self.user, self)
        dialog.exec()


    def add_facture_achat(self):
        dialog = AchatModule(self.db_connection,parent=self)
        dialog.exec()

    def open_hist_achat(self):
        dialog = GestHistStock(self.db_connection, parent=self)
        dialog.exec()

    def create_actions(self):
      
        self.act_validate = QAction(QIcon(":icon/ajouter.png"), "Ajouter un article", self)
        self.act_validate.triggered.connect(self.open_add_product_dialog)

        self.act_transform = QAction(QIcon(":icon/updated.png"), "Modifier", self)
        self.act_transform.triggered.connect(self.open_edit_product_dialog)

        self.act_pay = QAction(QIcon(":icon/delete.png"), "Supprimer", self)
        self.act_pay.triggered.connect(self.dele_product)

        self.act_print = QAction(QIcon(":icon/inventaire.png"), "Inventaire", self)
        self.act_print.setShortcut("Ctrl+P")
        self.act_print.triggered.connect(self.open_inventory)

        self.act_delete = QAction(QIcon(":icon/chariot-de-chariot.png"), "Ajouter une entrée", self)
        
        self.act_delete.triggered.connect((self.add_facture_achat))

        self.act_refresh = QAction(QIcon(":icon/refresh.png"), "Actualiser", self)
        self.act_refresh.setShortcut("F5")
        self.act_refresh.triggered.connect(self._refresh)

    def create_toolbar(self):
        toolbar = QToolBar("Actions Pièces", self)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        toolbar.addAction(self.act_validate)
        toolbar.addAction(self.act_transform)
        toolbar.addSeparator()
        toolbar.addAction(self.act_pay)
        toolbar.addAction(self.act_print)
        toolbar.addAction(self.act_delete)
        toolbar.addSeparator()
        toolbar.addAction(self.act_refresh)

        return toolbar
    # Data display
    # ---------------------------
   
    def _populate_table(self, data):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for item in data:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Reference
            ref = QTableWidgetItem(str(item["ref"]))

            # Nom
            nom_item = QTableWidgetItem(item["produit"])

            # Catégorie
            cat_item = QTableWidgetItem(item["categorie"])

            # Quantité (tri numérique réel)
            qty_item = QTableWidgetItem()
            qty_item.setData(Qt.ItemDataRole.DisplayRole, item["qty"])
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Prix achat
            prix_item = QTableWidgetItem()
            prix_item.setData(Qt.ItemDataRole.DisplayRole, float(item["price"]))
            prix_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Prix vente
            prix_item_vent = QTableWidgetItem()
            prix_item_vent.setData(Qt.ItemDataRole.DisplayRole, float(item["price_vent"]))
            prix_item_vent.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Statut
            statut_text = "OK" if item["qty"] >= item["alert_min"] else "Faible"
            statut_item = QTableWidgetItem(statut_text)

            if statut_text == "Faible":
                statut_item.setForeground(Qt.GlobalColor.red)

            # Insert
            self.table.setItem(row, 0, ref)
            self.table.setItem(row, 1, nom_item)
            self.table.setItem(row, 2, cat_item)
            self.table.setItem(row, 3, qty_item)
            self.table.setItem(row, 4, prix_item)
            self.table.setItem(row, 5, prix_item_vent)
            self.table.setItem(row, 6, statut_item)

            # Highlight ligne critique
            if statut_text == "Faible":
                for col in range(7):
                    self.table.item(row, col).setBackground(QColor("#FFE5E5"))

        self.table.setSortingEnabled(True)

    def _update_summary_cards(self, data):
        total_products = len(data)
        low_stock_alerts = sum(1 for p in data if p["qty"] < p["alert_min"])
        total_value = sum(p["qty"] * p["price"] for p in data)
        total_margin = sum(p["qty"] * (p["price_vent"] - p["price"]) for p in data)

        self.card_total.findChild(QLabel, "SummaryValue").setText(str(total_products))
        self.card_alerts.findChild(QLabel, "SummaryValue").setText(str(low_stock_alerts))
        self.card_value.findChild(QLabel, "SummaryValue").setText(
            self.cal.separateur_milieur(total_value)
        )
        self.card_marge.findChild(QLabel, "SummaryValue").setText(
            self.cal.separateur_milieur(total_margin)
    )

    def open_inventory(self):
        self.dialog = InventoryDialog(self.db_connection, self.user, parent=self)
        self.dialog.exec()

    def _refresh(self):
        data = self.dataSource.get_all_products()
        if not data:
            return

        self._populate_table(data)
        self._update_summary_cards(data)
        self.setWindowTitle(f"Gestion Stock - {len(data)} produits")
    # ---------------------------
    # Event Handlers    
    def open_add_product_dialog(self):
        dialog = AddProductDialog(db=self.db_connection,parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._refresh()
    
    def open_edit_product_dialog(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez une ligne avant de continuer 😎")
            return

        product_id = self.table.item(row, 0)
        if product_id is None:
            return

        dialog = EditProductDialog(self.db_connection, product_id.text(), parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._refresh()
    
    def dele_product(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Erreur", "Sélectionnez un produit ❌")
            return

        item = self.table.item(row, 0)
        if not item:
            return

        product_id = item.text()

        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Le produit sera archivé.\n"
            "Le stock et l'historique seront conservés.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        result = self.dataSource.delete_product(product_id, self.user)

        if result == "STOCK_EXISTANT":
            QMessageBox.warning(
                self,
                "Suppression impossible",
                "Ce produit possède encore du stock ❌"
            )
            return

        if result == "OK":
            QMessageBox.information(
                self,
                "Succès",
                "Produit archivé avec succès ✅"
            )
            self._refresh()
            return

        QMessageBox.critical(
            self,
            "Erreur",
            "Une erreur est survenue lors de la suppression ❌"
        )

    def filter_table(self, text):
        needle = text.strip().lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and needle in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)
