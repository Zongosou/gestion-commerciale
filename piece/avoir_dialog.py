from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QLabel
)
from PySide6.QtCore import Qt
from fonction.methode import cal

class AvoirDialog(QDialog):
    """
    Fenêtre de création d'avoir partiel ou total
    """

    def __init__(self, facture_id, db,parent=None):
        super().__init__(parent)
        self.facture_id = facture_id
        self.db = db
        self.cal = cal()
        self.setWindowTitle("Créer un avoir")
        self.resize(700, 400)

        self._build_ui()
        self._charger_lignes_facture()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            "Indiquez les quantités à avoir (0 = pas d'avoir sur la ligne)"
        )
        layout.addWidget(info)

        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "ID", "Produit", "Qté facturée", "Qté à avoir", "Prix"
        ])
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_ok = QPushButton("Valider l'avoir")
        self.btn_cancel = QPushButton("Annuler")

        self.btn_ok.clicked.connect(self._valider)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # Chargement des lignes facture
    # ------------------------------------------------------------------
    def _charger_lignes_facture(self):
        conn = self.cal.connect_to_db(self.db)
        if conn is None:
            QMessageBox.critical(self, "Erreur BD", "Impossible de se connecter à la base de données.")
            return
        cur = conn.cursor()

        cur.execute("""
            SELECT d.code, d.libelle, d.quantite, d.prix
            FROM vent d
            JOIN infov p ON p.factu = d.facture
            WHERE p.factu = ?
        """, (self.facture_id,))

        rows = cur.fetchall()
        self.table.setRowCount(len(rows))

        for r, (pid, name, qty, price) in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(str(pid)))
            self.table.setItem(r, 1, QTableWidgetItem(name))
            self.table.setItem(r, 2, QTableWidgetItem(str(qty)))

            item_avoir = QTableWidgetItem("0")
            item_avoir.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_avoir.setFlags(item_avoir.flags() | Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, 3, item_avoir)

            self.table.setItem(r, 4, QTableWidgetItem(str(price)))

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _valider(self):
        lignes = self.get_lignes_avoir()

        if not lignes:
            QMessageBox.warning(
                self,
                "Attention",
                "Aucune ligne sélectionnée pour l'avoir"
            )
            return

        self.accept()

    # ------------------------------------------------------------------
    # MÉTHODE CLÉ DEMANDÉE
    # ------------------------------------------------------------------
    def get_lignes_avoir(self):
        """
        Retourne les lignes à avoir sous forme :
        [
            {"product_id": int, "qty": float, "price": float},
            ...
        ]
        """
        lignes = []

        for row in range(self.table.rowCount()):
            try:
                qty_avoir = self.table.item(row, 3)
                if qty_avoir is None:
                    continue
                qty_avoir = float(qty_avoir.text())
            except (ValueError, AttributeError):
                continue

            if qty_avoir <= 0:
                continue

            qty_facturee = self.table.item(row, 2)
            if qty_facturee is None:
                continue
            qty_facturee = float(qty_facturee.text())
            if qty_avoir > qty_facturee:
                QMessageBox.warning(
                    self,
                    "Erreur",
                    "La quantité à avoir ne peut pas dépasser "
                    "la quantité facturée"
                )
                return []

            lignes.append({
                "product_id": str(self.table.item(row, 0).text()),
                "qty": qty_avoir,
                "price": float(self.table.item(row, 4).text())
            })

        return lignes

    