from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QMessageBox, QCheckBox,
    QWidget, QLabel, QComboBox, QHeaderView
)
from PySide6.QtGui import QIcon, QCursor
from PySide6.QtCore import Qt
import sqlite3 as sq


class ValidationInventaire(QDialog):
    def __init__(self, db_path,user=None, parent=None):
        super().__init__(parent)

        self.db_path = db_path
        self.user = user
        self.setWindowTitle("Validation des inventaires de stock")
        self.resize(620, 400)
        self.setWindowIcon(QIcon(":/icon/icone.png"))

        # ================= CONTROLES =================
        self.combo_statut = QComboBox()
        self.combo_statut.addItems(["Sélectionner le Statut", "Validé", "Annulée"])
        self.combo_statut.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.chk_all = QCheckBox("Tout sélectionner")
        self.chk_all.stateChanged.connect(self.toggle_all)

        # ================= TABLE =================
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Valider", "ID Inv", "Date", "Utilisateur", "Valeur Stock"]
        )

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 60)

        # ================= INFOS =================
        self.lbl_total = QLabel("Valeur sélectionnée : 0")
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignRight)

        # ================= BOUTON =================
        self.btn_valider = QPushButton("Valider la sélection")
        self.btn_valider.setEnabled(False)
        self.btn_valider.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_valider.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #94A3B8;
            }
        """)
        # ================= OPTION CORRECTION =================
        self.chk_correction = QCheckBox("Appliquer correction de stock après validation")
        self.chk_correction.setEnabled(False)
        self.combo_statut.currentTextChanged.connect(self._gerer_option_correction)
        self.btn_valider.clicked.connect(self.valider_selection)

        # ================= LAYOUT =================
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.combo_statut)
        top_layout.addWidget(self.chk_all)

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addWidget(self.table)
        layout.addWidget(self.lbl_total)
        layout.addWidget(self.chk_correction)
        layout.addWidget(self.btn_valider)

        self.charger_pieces()

    # ======================================================
    # CHARGEMENT DES INVENTAIRES
    # ======================================================
    def charger_pieces(self):
        self.table.setRowCount(0)
        self.chk_all.setChecked(False)
        self.btn_valider.setEnabled(False)
        self.lbl_total.setText("Valeur sélectionnée : 0")

        try:
            with sq.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, date_inv, user, valeur
                    FROM inventory
                    WHERE statut = 'BROUILLON'
                """)
                lignes = cur.fetchall()

                for row, ligne in enumerate(lignes):
                    self.table.insertRow(row)

                    chk = QCheckBox()
                    chk.stateChanged.connect(self._maj_ui)

                    widget = QWidget()
                    lay = QHBoxLayout(widget)
                    lay.addWidget(chk)
                    lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lay.setContentsMargins(0, 0, 0, 0)

                    self.table.setCellWidget(row, 0, widget)

                    for col, val in enumerate(ligne):
                        self.table.setItem(row, col + 1, QTableWidgetItem(str(val)))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    # ======================================================
    # UI LOGIC
    # ======================================================
    def toggle_all(self, state):
        for row in range(self.table.rowCount()):
            chk = self._get_checkbox(row)
            chk.setChecked(state == Qt.CheckState.Checked)

    def _get_checkbox(self, row):
        widget = self.table.cellWidget(row, 0)
        return widget.findChild(QCheckBox)

    def _maj_ui(self):
        total = 0
        selected = False

        for row in range(self.table.rowCount()):
            chk = self._get_checkbox(row)
            if chk.isChecked():
                selected = True
                total += float(self.table.item(row, 4).text())

        self.lbl_total.setText(f"Valeur sélectionnée : {total:,.0f}")
        self.btn_valider.setEnabled(selected)

    def valider_selection(self):
        statut = self.combo_statut.currentText()

        if statut not in ("Validé", "Annulée"):
            QMessageBox.warning(self, "Statut requis", "Veuillez sélectionner un statut valide.")
            return

        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Confirmer la mise à jour des inventaires en statut « {statut} » ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        try:
            with sq.connect(self.db_path) as conn:
                cur = conn.cursor()
                conn.execute("BEGIN IMMEDIATE")
                total = 0

                for row in range(self.table.rowCount()):
                    chk = self._get_checkbox(row)
                    if not chk.isChecked():
                        continue

                    inv_id = self.table.item(row, 1).text()

                    # ================= POPUP AVANT CORRECTION =================
                    appliquer_correction = False
                    if statut == "Validé" and self.chk_correction.isChecked():
                        popup = PopupCorrectionStock(self.db_path, inv_id, self)
                        if popup.exec() != QDialog.DialogCode.Accepted:
                            continue  # on saute cet inventaire seulement
                        appliquer_correction = True

                    # ================= UPDATE INVENTORY =================
                    if appliquer_correction:
                        cur.execute("""
                            UPDATE inventory
                            SET statut = ?, commentaire = ?, stock_corrige = 1
                            WHERE id = ?
                        """, (statut, "Inventaire validé avec correction", inv_id))

                        self.appliquer_correction_stock(cur, inv_id)

                    else:
                        cur.execute("""
                            UPDATE inventory
                            SET statut = ?, commentaire = ?, stock_corrige = 0
                            WHERE id = ?
                        """, (statut, "Inventaire validé sans correction", inv_id))

                    total += 1

                conn.commit()

            QMessageBox.information(
                self, "Succès",
                f"{total} inventaire(s) mis à jour avec succès."
            )

            self.charger_pieces()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _gerer_option_correction(self, text):
        self.chk_correction.setEnabled(text == "Validé")
        if text != "Validé":
            self.chk_correction.setChecked(False)
    
    def appliquer_correction_stock(self, cur, inventory_id):
        cur.execute("""
            SELECT product_ref, qty_reelle
            FROM inventory_items
            WHERE inventory_id = ?
        """, (inventory_id,))
        
        lignes = cur.fetchall()

        for product_id, qty_real in lignes:
            # Stock actuel
            cur.execute(
                "SELECT qty FROM stock WHERE id_libelle = ?",
                (product_id,)
            )
            row = cur.fetchone()
            stock_actuel = row[0] if row else 0

            difference = qty_real - stock_actuel

            if difference != 0:
                # Mise à jour du stock
                cur.execute("""
                    UPDATE stock SET qty = ? WHERE id_libelle = ?
                """, (qty_real, product_id))

                # Trace (audit)
                cur.execute("""
                    INSERT INTO stock_movement
                    (product_ref, qty, type, reference,user)
                    VALUES (?, ?, 'INVENTAIRE', ?,?)
                """, (product_id, difference, inventory_id,self.user))

class PopupCorrectionStock(QDialog):
    def __init__(self, db_path, inventory_id, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.inventory_id = inventory_id

        self.setWindowTitle("Détail des écarts de stock")
        self.resize(700, 420)

        # ================= TABLE =================
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Produit", "Stock théorique", "Stock inventorié", "Écart", "Action"
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # ================= BOUTONS =================
        self.btn_ok = QPushButton("Confirmer correction")
        self.btn_cancel = QPushButton("Annuler")

        self.btn_ok.setStyleSheet("""
            QPushButton { background-color:#16A34A; color:white;
            padding:8px 16px; border-radius:8px; font-weight:bold; }
        """)

        self.btn_cancel.setStyleSheet("""
            QPushButton { background-color:#DC2626; color:white;
            padding:8px 16px; border-radius:8px; font-weight:bold; }
        """)

        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        # ================= LAYOUT =================
        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_ok)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(btns)

        self.charger_ecarts()

    # ======================================================
    def charger_ecarts(self):
        try:
            with sq.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT 
                        p.name,
                        s.qty AS stock_theorique,
                        l.qty_reelle
                    FROM inventory_items l
                    JOIN products p ON p.ref = l.product_ref
                    JOIN stock s ON s.id_libelle = p.ref
                    WHERE l.inventory_id = ?
                """, (self.inventory_id,))

                lignes = cur.fetchall()
                self.table.setRowCount(0)

                for row, (name, stock, real) in enumerate(lignes):
                    ecart = real - stock
                    self.table.insertRow(row)

                    self.table.setItem(row, 0, QTableWidgetItem(name))
                    self.table.setItem(row, 1, QTableWidgetItem(str(stock)))
                    self.table.setItem(row, 2, QTableWidgetItem(str(real)))
                    self.table.setItem(row, 3, QTableWidgetItem(str(ecart)))

                    action = "➕ Augmentation" if ecart > 0 else "➖ Diminution" if ecart < 0 else "—"
                    item_action = QTableWidgetItem(action)

                    # 🎨 Couleurs
                    if ecart > 0:
                        item_action.setForeground(Qt.GlobalColor.darkGreen)
                    elif ecart < 0:
                        item_action.setForeground(Qt.GlobalColor.red)

                    self.table.setItem(row, 4, item_action)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def get_corrections(self):
        corrections = []
        conn = sq.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT p.ref, s.qty, l.qty_reelle
                FROM inventory_items l
                JOIN products p ON p.ref = l.product_ref
                JOIN stock s ON s.id_libelle = p.ref
                WHERE l.inventory_id = ?
            """, (self.inventory_id,))
            lignes = cur.fetchall()

            for product_ref, stock_theorique, stock_reel in lignes:
                ecart = stock_reel - stock_theorique
                if ecart != 0:
                    corrections.append((product_ref, ecart))
        finally:            conn.close()
        return corrections
    
    def accept(self):
        conn = sq.connect(self.db_path)

        corrections = self.get_corrections()
        
        if not corrections:
            QMessageBox.warning(self, "Aucun écart", "Aucun écart de stock à corriger.")
            return
        cur = conn.cursor()
        conn.execute("BEGIN IMMEDIATE")
        cmd = '''UPDATE stock SET qty = qty + ? WHERE id_libelle = ?'''
        for code, ecart in corrections:
            cur.execute(cmd, [ecart, code])
        cur.execute("""
                            UPDATE inventory
                            SET statut = ?, commentaire = ?, stock_corrige = 1
                            WHERE id = ?
                        """, ("Validé", "Inventaire validé avec correction", self.inventory_id))
        conn.commit()
        super().accept()
        QMessageBox.information(self, "Correction appliquée", "Les corrections de stock ont été appliquées avec succès.")