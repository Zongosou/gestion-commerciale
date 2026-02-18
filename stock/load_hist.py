from PySide6.QtWidgets import (
    QVBoxLayout, QTableWidget, QTableWidgetItem, QDialog, QMessageBox,QAbstractItemView
)
from PySide6.QtCore import Qt

from fonction.methode import cal
from stock.stock_db import DataManage


class GestHistStock(QDialog):
    def __init__(self, db_connection, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Historique des entrées par jour")
        self.resize(800, 600)
        self.layout_ = QVBoxLayout(self)
        self.setLayout(self.layout_)

        self.db_connection = db_connection
        self.cal = cal()
        self.dataSource = DataManage(db_connection)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Date",
            "Nb Factures",
            "Total Achat",
            "Total Payé",
            "Reste à payer",
            "Utilisateurs"
        ])

        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setWordWrap(True)
        self.layout_.addWidget(self.table)

        self._load_data()

    def _load_data(self):
        data = self.dataSource.get_supplier_debts_by_day()


        if not data:
            QMessageBox.information(
                self,
                "Information",
                "Aucune transaction d'entrée trouvée."
            )
            self.table.setRowCount(0)
            return

        self.table.setRowCount(len(data))
        self._populate_table(data)
        self._finalize_table()

    def _create_item(self, value, align_right=False):
        item = QTableWidgetItem(str(value))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        if align_right:
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        else:
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        return item

    def _populate_table(self, data):
        for row, item in enumerate(data):

            date_item = QTableWidgetItem(str(item["day"]))

            nb_item = QTableWidgetItem(str(item["nb_factures"] or 0))
            nb_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            total_achat = item["total_achat"] or 0
            achat_item = QTableWidgetItem(str(self.cal.separateur_milieur(total_achat)))
            achat_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            total_paye = item["total_paye"] or 0
            paye_item = QTableWidgetItem(str(self.cal.separateur_milieur(total_paye)))
            paye_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            total_reste = item["total_reste"] or 0
            reste_item = QTableWidgetItem(str(self.cal.separateur_milieur(total_reste)))
            reste_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            if total_reste > 0:
                reste_item.setForeground(Qt.GlobalColor.red)

            self.table.setItem(row, 0, date_item)
            self.table.setItem(row, 1, nb_item)
            self.table.setItem(row, 2, achat_item)
            self.table.setItem(row, 3, paye_item)
            self.table.setItem(row, 4, reste_item)
            self.table.setItem(row, 5, QTableWidgetItem(""))

    def _finalize_table(self):
        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

