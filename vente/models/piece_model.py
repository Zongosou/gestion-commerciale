from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex


class PieceTableModel(QAbstractTableModel):

    HEADERS = [
        "Facture",
        "ID Client",
        "Montant HT",
        "Montant TTC",
        "Paié",
        "Reste",
        "Statut Paiement",
        "Statut Pièce",
        "Utilisateur",
        "Date",
        "Type"
    ]

    def __init__(self, data=None):
        super().__init__()
        self._data = data or []

    # -------------------------

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if role == Qt.DisplayRole:
            return str(self._data[row][col])

        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    # -------------------------

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def get_row(self, row):
        return self._data[row] if 0 <= row < len(self._data) else None