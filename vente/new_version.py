from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QDoubleSpinBox, QPushButton,
    QTableView, QGroupBox, QAbstractItemView, QHeaderView,
    QCheckBox, QProgressBar, QMessageBox, QToolBar
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QAction
from PySide6.QtGui import QIcon


# =========================
# MODEL HAUTE PERFORMANCE
# =========================

class PanierModel(QAbstractTableModel):
    HEADERS = ["Code", "Désignation", "Quantité", "Prix", "Montant"]

    def __init__(self):
        super().__init__()
        self._data = []

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        item = self._data[row]

        if role == Qt.DisplayRole:
            if col == 0:
                return item["code"]
            if col == 1:
                return item["designation"]
            if col == 2:
                return item["quantite"]
            if col == 3:
                return f"{item['prix']:.2f}"
            if col == 4:
                return f"{item['montant']:.2f}"

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def add_item(self, item):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self._data.append(item)
        self.endInsertRows()

    def remove_item(self, row):
        if 0 <= row < len(self._data):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._data.pop(row)
            self.endRemoveRows()

    def clear(self):
        self.beginResetModel()
        self._data.clear()
        self.endResetModel()

    def total_ht(self):
        return sum(i["montant"] for i in self._data)


# =========================
# CLASSE VENTE COMPLETE
# =========================

class Vente(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vente - Ultra Optimisée")
        self.resize(1200, 700)

        self._init_ui()
        self._init_model()
        self._init_connections()

    # ================= UI =================

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)

        # ---------- Client ----------
        client_layout = QHBoxLayout()
        self.client_line = QLineEdit()
        client_layout.addWidget(QLabel("Client:"))
        client_layout.addWidget(self.client_line)
        main.addLayout(client_layout)

        # ---------- Article ----------
        article_layout = QHBoxLayout()

        self.code_line = QLineEdit()
        self.designation_line = QLineEdit()
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setMaximum(999999)
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setMaximum(999999999)
        self.price_spin.setDecimals(2)

        self.add_btn = QPushButton("Ajouter")

        article_layout.addWidget(QLabel("Code"))
        article_layout.addWidget(self.code_line)
        article_layout.addWidget(QLabel("Désignation"))
        article_layout.addWidget(self.designation_line)
        article_layout.addWidget(QLabel("Qté"))
        article_layout.addWidget(self.qty_spin)
        article_layout.addWidget(QLabel("Prix"))
        article_layout.addWidget(self.price_spin)
        article_layout.addWidget(self.add_btn)

        main.addLayout(article_layout)

        # ---------- Table ----------
        self.table = QTableView()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        main.addWidget(self.table, 1)

        # ---------- Paiement ----------
        pay_group = QGroupBox("Paiement")
        pay_layout = QVBoxLayout()

        row1 = QHBoxLayout()

        self.tva_check = QCheckBox("TVA")
        self.tva_spin = QDoubleSpinBox()
        self.tva_spin.setSuffix(" %")

        self.paid_spin = QDoubleSpinBox()
        self.paid_spin.setMaximum(999999999)
        self.paid_spin.setDecimals(2)

        row1.addWidget(self.tva_check)
        row1.addWidget(self.tva_spin)
        row1.addWidget(QLabel("Montant versé"))
        row1.addWidget(self.paid_spin)

        pay_layout.addLayout(row1)

        row2 = QHBoxLayout()

        self.ht_label = QLabel("0.00")
        self.ttc_label = QLabel("0.00")
        self.reste_label = QLabel("0.00")

        row2.addWidget(QLabel("HT:"))
        row2.addWidget(self.ht_label)
        row2.addWidget(QLabel("TTC:"))
        row2.addWidget(self.ttc_label)
        row2.addWidget(QLabel("Reste:"))
        row2.addWidget(self.reste_label)

        pay_layout.addLayout(row2)

        self.progress = QProgressBar()
        pay_layout.addWidget(self.progress)

        pay_group.setLayout(pay_layout)
        main.addWidget(pay_group)

        # Toolbar
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        self.action_validate = QAction("Valider", self)
        self.action_new = QAction("Nouvelle", self)

        toolbar.addAction(self.action_validate)
        toolbar.addAction(self.action_new)

    # ================= MODEL =================

    def _init_model(self):
        self.model = PanierModel()
        self.table.setModel(self.model)

    # ================= CONNECTIONS =================

    def _init_connections(self):
        self.add_btn.clicked.connect(self.add_article)
        self.tva_check.stateChanged.connect(self.update_totals)
        self.tva_spin.valueChanged.connect(self.update_totals)
        self.paid_spin.valueChanged.connect(self.update_totals)
        self.action_new.triggered.connect(self.reset_form)

    # ================= LOGIQUE =================

    def add_article(self):
        code = self.code_line.text()
        designation = self.designation_line.text()
        qty = self.qty_spin.value()
        price = self.price_spin.value()

        if not code or qty <= 0:
            QMessageBox.warning(self, "Erreur", "Article invalide.")
            return

        montant = qty * price

        item = {
            "code": code,
            "designation": designation,
            "quantite": qty,
            "prix": price,
            "montant": montant
        }

        self.model.add_item(item)
        self.update_totals()

        self.code_line.clear()
        self.designation_line.clear()
        self.qty_spin.setValue(0)
        self.price_spin.setValue(0)

    def update_totals(self):
        total_ht = self.model.total_ht()

        tva = 0
        if self.tva_check.isChecked():
            tva = total_ht * (self.tva_spin.value() / 100)

        total_ttc = total_ht + tva
        paid = self.paid_spin.value()
        reste = total_ttc - paid

        self.ht_label.setText(f"{total_ht:,.2f}")
        self.ttc_label.setText(f"{total_ttc:,.2f}")
        self.reste_label.setText(f"{reste:,.2f}")

        percent = 0 if total_ttc == 0 else int((paid / total_ttc) * 100)
        self.progress.setValue(max(0, min(percent, 100)))

    def reset_form(self):
        self.model.clear()
        self.client_line.clear()
        self.paid_spin.setValue(0)
        self.update_totals()
