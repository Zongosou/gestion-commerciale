from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton,
    QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt
from stock.stock_db import DataManage

class SupplierPaymentDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paiement Fournisseur")
        self.resize(700, 500)

        self.data = DataManage(db)

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Facture", "Date", "Montant", "Payé", "Reste"]
        )
        layout.addWidget(self.table)

        self.input_amount = QLineEdit()
        self.input_amount.setPlaceholderText("Montant à payer")
        layout.addWidget(self.input_amount)

        pay_btn = QPushButton("Payer")
        pay_btn.clicked.connect(self.pay_invoice)
        layout.addWidget(pay_btn)

        self.load_data()

    def load_data(self):
        data = self.data.get_unpaid_supplier_invoices()
        self.table.setRowCount(len(data))

        for row, item in enumerate(data):
            for col, key in enumerate(item):
                cell = QTableWidgetItem(str(item[key]))
                if key == "reste":
                    cell.setForeground(Qt.GlobalColor.red)
                self.table.setItem(row, col, cell)

    def pay_invoice(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Erreur", "Sélectionnez une facture.")
            return

        facture = self.table.item(selected, 0).text()

        try:
            montant = float(self.input_amount.text())
        except:
            QMessageBox.warning(self, "Erreur", "Montant invalide.")
            return

        result = self.data.pay_supplier_invoice(facture, montant, "ADMIN")

        if result == "OK":
            QMessageBox.information(self, "Succès", "Paiement enregistré.")
            self.load_data()
        elif result == "DEPASSEMENT":
            QMessageBox.warning(self, "Erreur", "Montant dépasse le reste.")
        else:
            QMessageBox.critical(self, "Erreur", "Erreur paiement.")
