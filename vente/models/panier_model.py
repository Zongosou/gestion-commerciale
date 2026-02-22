from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex


class PanierModel(QAbstractTableModel):

    HEADERS = [
        "Code",
        "Désignation",
        "Qté",
        "Prix Vente",
        "Remise %",
        "Prix Net",
        "Prix Achat",
        "Marge",
        "Montant"
    ]

    def __init__(self, stock_cache=None):
        super().__init__()
        self._data = []
        self.stock_cache = stock_cache or {}

    # ---------------------
    # Base
    # ---------------------

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if role in (Qt.DisplayRole, Qt.EditRole):
            return self._data[row][col]

        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        if index.column() in (2, 3, 4):
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    # ---------------------
    # Edition cellule
    # ---------------------

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole:
            return False

        row = index.row()
        col = index.column()

        try:
            value = float(value)
            self._data[row][col] = value
            self._recalculate_row(row)
            self.dataChanged.emit(index, index)
            return True
        except:
            return False

    # ---------------------
    # Gestion données
    # ---------------------

    def add_article(self, code, designation, qte, prix_vente, prix_achat=None):
        if prix_achat is None:
            prix_achat = 0.0

        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())

        remise = 0.0
        prix_net = prix_vente
        marge = prix_net - prix_achat
        montant = qte * prix_net

        self._data.append([
            code,
            designation,
            qte,
            prix_vente,
            remise,
            prix_net,
            prix_achat,
            marge,
            montant
        ])

        self.endInsertRows()

    def remove_row(self, row):
        if 0 <= row < self.rowCount():
            self.beginRemoveRows(QModelIndex(), row, row)
            self._data.pop(row)
            self.endRemoveRows()

    def get_total_ht(self):
        return sum(row[8] for row in self._data)

    def get_total_marge(self):
        return sum(row[7] * row[2] for row in self._data)

    def get_all_data(self):
        return self._data

    # ---------------------
    # Recalcul interne
    # ---------------------

    def _recalculate_row(self, row):

        code, designation, qte, prix_vente, remise, _, prix_achat, _, _ = self._data[row]

        # Calcul remise
        prix_net = prix_vente - (prix_vente * remise / 100)

        # Marge
        marge = prix_net - prix_achat

        # Montant
        montant = qte * prix_net

        self._data[row][5] = round(prix_net, 2)
        self._data[row][7] = round(marge, 2)
        self._data[row][8] = round(montant, 2)
