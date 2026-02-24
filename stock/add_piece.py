
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QComboBox, QDateEdit, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox,
    QSizePolicy, QDoubleSpinBox, QHeaderView
)
from PySide6.QtGui import QIcon, QDoubleValidator
from PySide6.QtCore import Qt, QDate
from datetime import datetime
import sqlite3
from fonction.methode import cal

class AchatModule(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Gestion des Achats et Réception de Stock")
        self.setWindowIcon(QIcon(":/icon/icone.png"))
        self.setMinimumSize(700, 600)
        self.setMaximumSize(700,600)

        self.db = db_manager
        self.cal = cal()
        self.charged = self.cal.charger_configuration_paie()
        charge_devise = self.cal.charger_tva_devise(self.db)
        # Configuration par défaut si non trouvée
        self.devise = charge_devise["devise"] if charge_devise else "CFA"
        self.current_user = "Utilisateur Test"

        self.initUI()
        self.get_id_fournisseur()

    # ---------------------------------------------------
    # UI
    # ---------------------------------------------------
    def initUI(self):
        main_layout = QVBoxLayout(self)

        # ================= HEADER =================
        header_group = QGroupBox("Détails de la Facture Fournisseur")
        header_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        header_layout = QFormLayout(header_group)

        self.type_facture_input = QLineEdit()
        self.ref_input = QLineEdit()
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")

        self.id_fournisseur_input = QComboBox()
        self.id_fournisseur_input.currentIndexChanged.connect(self.get_info_fournisseur)

        self.fournisseur_input = QLineEdit()
        self.fournisseur_input.setReadOnly(True)

        self.statut_combo = QComboBox()
        self.statut_combo.addItems(["En attente de paiement","Partiellement payée", "Payée"])

        header_layout.addRow("Type de Facture :", self.type_facture_input)
        header_layout.addRow("Référence :", self.ref_input)
        header_layout.addRow("Date de Réception :", self.date_input)
        header_layout.addRow("ID Fournisseur :", self.id_fournisseur_input)
        header_layout.addRow("Fournisseur :", self.fournisseur_input)
        header_layout.addRow("Statut :", self.statut_combo)

        main_layout.addWidget(header_group)

        # ================= TABLE =================
        lines_group = QGroupBox("Produits Achetés")
        lines_layout = QVBoxLayout(lines_group)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Produit", "Quantité", "Prix Achat", "Total"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        lines_layout.addWidget(self.table, 1)

        add_btn = QPushButton("Ajouter un Produit")
        add_btn.setObjectName("IconButton")
        add_btn.setIcon(QIcon(":/icon/ajouter.png"))
        add_btn.clicked.connect(self.add_product_line)

        lines_layout.addWidget(add_btn, 0, Qt.AlignmentFlag.AlignLeft)

        main_layout.addWidget(lines_group)

        # ================= ACTIONS =================
        action_group = QGroupBox("Actions")
        action_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        action_layout = QHBoxLayout(action_group)

        self.total_label = QLabel(f"Montant Total ({self.devise})")
        self.total_label.setStyleSheet("font-weight:bold;")
        self.total_input = QLabel("0,00")
        self.total_input.setStyleSheet("font-weight:bold;")
        self.input_payed = QDoubleSpinBox()
        self.input_payed.setMaximum(999999999)
        
        save_btn = QPushButton("Valider et Mettre à Jour le Stock")
        save_btn.setObjectName("IconButton")
        save_btn.setIcon(QIcon(":icon/liste-de-courses.png"))
        save_btn.clicked.connect(self.save_and_update_stock)

        action_layout.addWidget(self.total_label)
        action_layout.addStretch()
        action_layout.addWidget(self.total_input)
        action_layout.addStretch()
        action_layout.addWidget(QLabel("Montant Payé :"))
        action_layout.addStretch()
        action_layout.addWidget(self.input_payed)
        action_layout.addStretch()
        action_layout.addWidget(save_btn)

        main_layout.addWidget(action_group)

        # ================= STRETCH =================
        main_layout.setStretch(0, 0)  # Header fixe
        main_layout.setStretch(1, 1)  # Tableau flexible
        main_layout.setStretch(2, 0)  # Actions fixes

    # ---------------------------------------------------
    # FOURNISSEURS
    # ---------------------------------------------------
    def get_id_fournisseur(self):
        conn = self.cal.connect_to_db(self.db)
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT id, nom FROM client WHERE type='Fournisseur'")
            for i, n in cur.fetchall():
                self.id_fournisseur_input.addItem(f"{i} - {n}", i)
            conn.close()

    def get_info_fournisseur(self):
        conn = self.cal.connect_to_db(self.db)
        if conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT nom FROM client WHERE id=?",
                (self.id_fournisseur_input.currentData(),)
            )
            r = cur.fetchone()
            if r:
                self.fournisseur_input.setText(r[0])
            conn.close()

    # ---------------------------------------------------
    # TABLE
    # ---------------------------------------------------
    def load_all_products(self):
        """Charge tous les produits disponibles dans le stock."""
        products = []
        conn=self.cal.connect_to_db(self.db)
        if conn:
            cursor=conn.cursor()
            query="SELECT ref, name, price FROM products"
            cursor.execute(query)
            result=cursor.fetchall()
            for row in result:
                pid, nom, price = row
                products.append({"id": pid, "nom": nom, "price": price})
            conn.close()
        return products
    def add_product_line(self):
        row = self.table.rowCount()
        self.table.insertRow(row)

        combo = QComboBox()
        combo.addItem("Sélectionner...", None)
        for p in self.load_all_products():
            combo.addItem(p["nom"], p["id"])
        combo.currentIndexChanged.connect(self.recalculate_totals)

        qty = QDoubleSpinBox()
        qty.setMinimum(0)
        qty.setMaximum(99999)
        qty.valueChanged.connect(self.recalculate_totals)

        price = QDoubleSpinBox()
        price.setMinimum(0)
        price.setMaximum(999999999999)
        price.setDecimals(2)
        price.valueChanged.connect(self.recalculate_totals)

        total = QTableWidgetItem("0,00")
        total.setFlags(total.flags() & ~Qt.ItemFlag.ItemIsEditable)

        self.table.setCellWidget(row, 0, combo)
        self.table.setCellWidget(row, 1, qty)
        self.table.setCellWidget(row, 2, price)
        self.table.setItem(row, 3, total)

    def recalculate_totals(self):
        total_general = 0.0
        for r in range(self.table.rowCount()):
            qty = self.table.cellWidget(r, 1).value()
            price = self.table.cellWidget(r, 2).value()
            total = qty * price
            total_general += total
            self.table.item(r, 3).setText(f"{total:,.2f}".replace(".", ","))

        self.total_input.setText(
            f"{total_general}"
        )
    def get_status(self):
        total = float(self.total_input.text())
        payed = self.input_payed.value()
        rested = total - payed

        if rested == 0:
            return "Payée"
        elif rested < 0:
            return "Partiellement payée"
        else:
            return "En attente de paiement"
    # ---------------------------------------------------
    # SAUVEGARDE
    # ---------------------------------------------------
    def save_and_update_stock(self):
        ref = self.ref_input.text().strip()
        type_piece = self.type_facture_input.text().strip()
        fournisseur_id = self.id_fournisseur_input.currentData()
        date_now = datetime.now().isoformat()

        if not ref:
            QMessageBox.warning(self, "Erreur", "Veuillez saisir une référence de facture.")
            return

        lignes = self._get_lignes_facture()
        if not lignes:
            QMessageBox.warning(
                self,
                "Erreur",
                "Veuillez ajouter au moins un produit avec une quantité valide."
            )
            return

        # Sécurisation montant payé
        try:
            montant_paye = self.input_payed.value()
            print(montant_paye)
        except:
            montant_paye = 0.0
        
        montant_total = float(self.total_input.text())

        conn = self.cal.connect_to_db(self.db)
        if not conn:
            QMessageBox.critical(self, "Erreur", "Connexion à la base impossible.")
            return

        try:
            cur = conn.cursor()
            conn.execute("BEGIN IMMEDIATE")

            # ==============================
            # 1️⃣ INSERT FACTURE (TABLE info)
            # ==============================
            cur.execute("""
                INSERT INTO info (
                    factu, id_fr, montant, mnt_paye,
                    datee, type_piece, utilisateur,status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?,?)
            """, (
                ref,
                fournisseur_id,
                montant_total,
                montant_paye,
                date_now,
                type_piece,
                self.current_user,
                self.get_status()
            ))

            # ==============================
            # 2️⃣ TRAITEMENT DES LIGNES
            # ==============================
            for produit_id, quantite, prix_achat in lignes:

                # Récupérer ancien stock
                cur.execute(
                    "SELECT qty, price FROM stock WHERE id_libelle = ?",
                    (produit_id,)
                )
                row = cur.fetchone()

                old_qty = row[0] if row else 0
                old_price = row[1] if row else 0

                new_qty = old_qty + quantite

                # ==============================
                # 🔥 CALCUL COÛT MOYEN PONDÉRÉ
                # ==============================
                if old_qty > 0:
                    new_price = (
                        (old_qty * old_price) +
                        (quantite * prix_achat)
                    ) / new_qty
                else:
                    new_price = prix_achat

                # ==============================
                # UPDATE / INSERT STOCK
                # ==============================
                cur.execute("""
                    INSERT INTO stock (id_libelle, qty, price)
                    VALUES (?, ?, ?)
                    ON CONFLICT(id_libelle)
                    DO UPDATE SET
                        qty = excluded.qty,
                        price = excluded.price
                """, (
                    produit_id,
                    new_qty,
                    new_price
                ))

                # ==============================
                # HISTORIQUE STOCK
                # ==============================
                cur.execute("""
                    INSERT INTO stock_history (
                        product_id, old_qty, new_qty,
                        type, user, date, comment
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    produit_id,
                    old_qty,
                    new_qty,
                    "ENTREE",
                    self.current_user,
                    date_now,
                    f"Achat {ref}"
                ))

                # ==============================
                # HIST FACTURE
                # ==============================
                cur.execute("""
                    INSERT INTO hist (
                        fact, code, prix,
                        quantite, montant,
                        tdate, id_four,
                        type_piece, utilisateur
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ref,
                    produit_id,
                    prix_achat,
                    quantite,
                    quantite * prix_achat,
                    date_now,
                    fournisseur_id,
                    type_piece,
                    self.current_user
                ))

            conn.commit()

            QMessageBox.information(
                self,
                "Succès",
                "Facture enregistrée et stock mis à jour avec succès."
            )

            self.accept()

        except Exception as e:
            conn.rollback()
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de la sauvegarde : {e}"
            )
        finally:
            conn.close()

    def _get_lignes_facture(self):
        lignes = []
        for row in range(self.table.rowCount()):
            combo = self.table.cellWidget(row, 0)
            qty = self.table.cellWidget(row, 1)
            price = self.table.cellWidget(row, 2)
            if combo is None or qty is None or price is None:
                continue
            produit_id = combo.currentData()
            if produit_id is None:
                continue
            quantite = float(qty.value())
            prix = float(price.value())
            if quantite <= 0:
                continue
            lignes.append((produit_id, quantite, prix))
        return lignes
