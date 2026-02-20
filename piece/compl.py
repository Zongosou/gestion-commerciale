from PySide6.QtGui import  QIcon,QCursor
from PySide6.QtWidgets import (QDialog, QMessageBox, QPushButton, QVBoxLayout,
                             QTableWidget,QComboBox, QTableWidgetItem,QHBoxLayout,QCheckBox,QWidget,QInputDialog,QAbstractItemView)
import sqlite3 as sq
from PySide6.QtCore import Qt
from datetime import date, datetime
from fonction.methode import Numeroteur, cal
from vente.ventDB import DataManage
from vente.application.valider_piece import ValiderPieceUseCase

STATUT_PIECE = {
    "Devis": ["En cours", "Validé", "Traité", "Annulée"],
    "Commande": ["En cours", "Validé", "Traité", "Annulée"],
    "Bon de livraison": ["En cours", "Validé", "Traité", "Annulée"],
    "Facture": ["Brouillon", "Validée", "Traité", "Annulée"]
}

class ReliquatManager(QDialog):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.setWindowTitle("Traitement des reliquats")
        
        self.setWindowIcon(QIcon(':/icon/icone.png'))
        self.btn_traiter = QPushButton("Compléter les reliquats")
        self.btn_traiter.clicked.connect(self.completer_reliquats)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setTabKeyNavigation(True)
        self.table.setProperty("showDropIndicator", True)
        self.table.setDragEnabled(False)
        self.table.setDragDropOverwriteMode(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Code", "Produit", "Client", "Qté restante", "Qté initiale", "Facture"])

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addWidget(self.btn_traiter)
        self.setLayout(layout)
        self.charger_reliquats()

    def charger_reliquats(self):
        self.table.setRowCount(0)
        try:
            with sq.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT code, libelle, client, quantite, qtit_entente, facture
                    FROM liste 
                    WHERE quantite > 0
                """)
                lignes = cur.fetchall()

                for row_num, row_data in enumerate(lignes):
                    self.table.insertRow(row_num)
                    for col_num, value in enumerate(row_data):
                        self.table.setItem(row_num, col_num, QTableWidgetItem(str(value)))
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors du chargement des reliquats : {str(e)}")

    def completer_reliquats(self):
        try:
            with sq.connect(self.db_path) as conn:
                cur = conn.cursor()

                cur.execute("""
                    SELECT client, code, facture, libelle, prix, quantite, qtit_entente, id_ui
                    FROM liste 
                    WHERE quantite > 0
                """)
                lignes = cur.fetchall()

                if not lignes:
                    QMessageBox.information(self, "Aucun reliquat", "Aucun article en attente de livraison/facturation.")
                    return

                for ligne in lignes:
                    client, code, facture, libelle, prix, qte_restante, qtit_entente, id_ui = ligne

                    cur.execute("SELECT quantite FROM achat WHERE code = ?", (code,))
                    stock_row = cur.fetchone()
                    stock_dispo = stock_row[0] if stock_row else 0

                    if stock_dispo == 0:
                        continue

                    qte_facturable = min(stock_dispo, qte_restante)
                    reste = qte_restante - qte_facturable
                    montant = round(prix * qte_facturable, 2)

                    if qte_facturable > 0:
                        cur.execute("UPDATE achat SET quantite = quantite - ? WHERE code = ?", (qte_facturable, code))

                        cur.execute("""
                            INSERT INTO vent (client, code, facture, libelle, prix, quantite, montant, datee, rest, id_ui)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            client, code, facture + "_suite", libelle, prix,
                            qte_facturable, montant, date.today().isoformat(), reste, id_ui
                        ))

                        cur.execute("""
                            UPDATE liste 
                            SET quantite = ?
                            WHERE code = ? AND facture = ?
                        """, (reste, code, facture))

                conn.commit()
                QMessageBox.information(self, "Succès", "Les reliquats disponibles ont été automatiquement facturés.")
                self.charger_reliquats()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Une erreur est survenue : {str(e)}")


class DialogueConversion(QDialog):
    def __init__(self, db_path,user):
        super().__init__()
        self.db_path = db_path
        self.user = user or "Admin"
        self.cal = cal()
        self.numeroteur = Numeroteur(self.db_path)
        self.setWindowTitle("Pièces à convertir")
        self.resize(520, 350)
        self.setWindowIcon(QIcon(':/icon/icone.png'))
        
        self.combo_type = QComboBox()
        LISTE_PIECES = ["Devis","Commande", "Bon de livraison", "Facture"]
        self.combo_type.addItems(LISTE_PIECES)
        self.combo_type.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.combo_type.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setTabKeyNavigation(True)
        self.table.setProperty("showDropIndicator", True)
        self.table.setDragEnabled(False)
        self.table.setDragDropOverwriteMode(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["", "N° pièce", "Client", "Date", "Montant"])

        btn_ok = QPushButton("Convertir")
        btn_ok.setStyleSheet("""
                
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
            
            """
        )
        btn_ok.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_annuler = QPushButton("Annuler")
        btn_annuler.setStyleSheet("""
                
                background-color: #EF4444;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
            
            """
        )
        btn_annuler.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_ok.clicked.connect(self.convertir_piece)
        btn_annuler.clicked.connect(self.reject)
        self.combo_type.currentTextChanged.connect(self.charger_pieces)

        layout_main = QVBoxLayout()
        layout_main.addWidget(self.combo_type)
        layout_main.addWidget(self.table)

        btns = QHBoxLayout()
        btns.addWidget(btn_ok)
        btns.addWidget(btn_annuler)

        layout_main.addLayout(btns)
        self.setLayout(layout_main)

        self.charger_pieces()

    def charger_pieces(self):
        type_piece = self.combo_type.currentText()
        self.table.setRowCount(0)

        try:
            with sq.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT factu, client, datee, montant
                    FROM infov
                    WHERE type_fact = ? AND statut_piece = 'Validé'
                """, (type_piece,))
                resultats = cur.fetchall()

                for row_num, ligne in enumerate(resultats):
                    self.table.insertRow(row_num)
                    checkbox = QCheckBox()
                    checkbox_widget = QWidget()
                    layout = QHBoxLayout(checkbox_widget)
                    layout.addWidget(checkbox)
                    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.setContentsMargins(0, 0, 0, 0)
                    self.table.setCellWidget(row_num, 0, checkbox_widget)

                    for col_num, val in enumerate(ligne):
                        self.table.setItem(row_num, col_num + 1, QTableWidgetItem(str(val)))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur de chargement des pièces : {e}")
    
    # Vérification de doublon avant conversion
    def piece_deja_convertie(self, factu_origine, type_cible):
        with sq.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) FROM infov
                WHERE origine = ? AND type_fact = ?
            """, (factu_origine, type_cible))
            return cur.fetchone()[0] > 0

    def convertir_piece(self):

        selected = None
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if widget and widget.findChild(QCheckBox).isChecked():
                selected = row
                break

        if selected is None:
            QMessageBox.warning(self, "Aucune sélection", "Veuillez cocher une pièce à convertir.")
            return

        self.table.selectRow(selected)
        add_ = self.add_ajt()
        if add_ is None:
            return

        res, resultat, client, cb_ = add_
        if not res:
            return

        type_origine = self.combo_type.currentText()
        factu_origine = res[1]

        type_cible, ok = QInputDialog.getItem(
            self, "Conversion", "Convertir en :", cb_, editable=False
        )

        if not ok or not type_cible:
            return

        # 🔒 Vérification AVANT TOUT
        if self.piece_deja_convertie(factu_origine, type_cible):
            QMessageBox.warning(
                self,
                "Conversion impossible",
                f"La pièce {factu_origine} a déjà été convertie en {type_cible}."
            )
            return

        # Génération numéro
        mapping = {
            "Facture": "FAC",
            "Bon de livraison": "BL",
            "Commande": "CMD",
            "Devis": "DV"
        }

        if type_cible not in mapping:
            QMessageBox.warning(self, "Erreur", "Type de pièce inconnu")
            return

        nouveau_numero = self.numeroteur.generer(mapping[type_cible])

        try:
            with sq.connect(self.db_path) as conn:
                cur = conn.cursor()

                # ===== Création pièce cible =====
                cur.execute("""
                    INSERT INTO infov (
                        factu, client, montant, mnt_ttc,
                        payer, monn, datee, statut_piece,statut_paiement,
                        type_fact, origine, utilisateur, date_validation
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)
                """, (
                    nouveau_numero,
                    res[2],
                    res[3],
                    res[4],
                    0.0,
                    0.0,
                    res[7],
                    "En cours",
                    "N/A",
                    type_cible,
                    factu_origine,
                    self.user,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

                # ===== Insertion lignes =====
                for article in resultat:
                    code, libelle, quantite, prix, montant = article

                    if type_cible == "Facture":
                        cur.execute("""
                            INSERT INTO vent (
                                client, code, facture,
                                libelle, prix, quantite,
                                montant, datee, id_clt
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            client, code, nouveau_numero,
                            libelle, prix, quantite,
                            montant, res[8], res[1]
                        ))

                    else:
                        cur.execute("""
                            INSERT INTO liste (
                                client, code, facture,
                                libelle, prix, quantite,
                                montant, datee, id_clt
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            client, code, nouveau_numero,
                            libelle, prix, quantite,
                            montant, res[8], res[2]
                        ))

                # ===== Mise à jour pièce origine =====
                cur.execute("""
                    UPDATE infov
                    SET statut_piece='Traité'
                    WHERE factu=?
                """, (factu_origine,))

                # ===== Statut paiement si facture =====
                if type_cible == "Facture":
                    cur.execute("""
                        UPDATE infov
                        SET statut_paiement='Impayé'
                        WHERE factu=?
                    """, (nouveau_numero,))

                conn.commit()

            QMessageBox.information(
                self,
                "Succès",
                f"{type_origine} {factu_origine} converti en {type_cible} ({nouveau_numero})"
            )

            self.charger_pieces()

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors du transfert : {e}")
    
    # Optionnel : ouvrir la pièce créée
    # self.open_piece(type_cible, nouveau_numero)
    def add_ajt(self):
        conn = cal.connect_to_db(self.db_path)
        if conn is None:
            QMessageBox.warning(self, "Erreur", "Impossible de se connecter à la base de données.")
            return None, [], "", []
        cur = conn.cursor()
        try:
            index = None
            for row in range(self.table.rowCount()):
                widget = self.table.cellWidget(row, 0)
                if widget and widget.findChild(QCheckBox).isChecked():
                    index = row
                    break
            if index is None:
                QMessageBox.warning(self, "Transfert", "Veuillez cocher une ligne à convertir!")
                return None, [], "",[]

            va_item = self.table.item(index, 1)
            va = va_item.text() if va_item else ""
            sql = '''SELECT * FROM infov WHERE factu=?'''
            cur = cur.execute(sql, [va])
            res = cur.fetchone()
            if not res:
                QMessageBox.warning(self, "Transfert", "Pièce introuvable.")
                return [], [], "",[]

            status = str(res[10]).upper()
            if status not in ["VALIDÉ", "VALIDÉE"]:
                QMessageBox.warning(self, "Conversion refusée", f"La pièce sélectionnée n'est pas validée. Statut actuel : {res[10]}")
                return [], [], "",[]
            cb_ = []
            resultat = []
            type_fact = self.combo_type.currentText()
            self.type = type_fact
            if self.type == "Devis":
                cb_ = ["Commande", "Bon de livraison", "Facture"]
            elif self.type == "Commande":
                cb_ = ["Bon de livraison", "Facture"]
            elif self.type == "Bon de livraison":
                cb_ = ["Facture"]

            deta = '''SELECT code, libelle, quantite, prix, montant FROM liste WHERE facture=?'''
            resultat = cur.execute(deta, [va]).fetchall()
            if not resultat:
                QMessageBox.information(self, "Erreur", "Liste des articles indisponible")
                return [], [], "", []
            try:
                ui = '''SELECT client FROM liste WHERE facture=?'''
                client = str(cur.execute(ui, [va]).fetchone()[0])
            except:
                QMessageBox.information(self, "Erreur", "Information du client indisponible")
                client = ""

            return res, resultat, client, cb_

        except Exception as e:
            QMessageBox.information(self, "Erreur", f"Erreur : {e}")

class ValidationPieces(QDialog):
    def __init__(self, db_path,user):
        super().__init__()
        self.db_path = db_path
        self.user = user
        self.setWindowTitle("Valider des pièces")
        self.resize(520, 350)
        self.setWindowIcon(QIcon(':/icon/icone.png'))
        

        self.validator = ValiderPieceUseCase(
            dbsource=DataManage(self.db_path),
            cal=cal
        )

        self.combo_type = QComboBox()
        self.combo_type.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.combo_type.addItems(["Selectionner le Type de Pièce","Devis", "Commande", "Bon de livraison","Facture"])
        self.combo_type.currentTextChanged.connect(self.charger_pieces)
        self.combo_statut = QComboBox()
        self.combo_statut.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setTabKeyNavigation(True)
        self.table.setProperty("showDropIndicator", True)
        self.table.setDragEnabled(False)
        self.table.setDragDropOverwriteMode(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Valider", "N° Pièce", "Client", "Date", "Montant"])

        self.btn_valider = QPushButton("Valider la sélection")
        self.btn_valider.setStyleSheet("""
                
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
            
            """
        )
        self.btn_valider.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_valider.clicked.connect(self.valider_selection)
        box_h = QHBoxLayout()
        box_h.addWidget(self.combo_type)
        box_h.addWidget(self.combo_statut)
        layout = QVBoxLayout()
        layout.addLayout(box_h)
        layout.addWidget(self.table)
        layout.addWidget(self.btn_valider)
        
        self.setLayout(layout)
        self.charger_pieces()

    def get_statut(self,piece:str):
        return STATUT_PIECE.get(piece,[])
    
    def mette_a_jour(self,piece):
        self.combo_statut.clear()
        self.combo_statut.addItems(self.get_statut(piece))
    def charger_pieces(self):
        type_piece = self.combo_type.currentText()
        self.table.setRowCount(0)
        self.mette_a_jour(type_piece)
        try:
            with sq.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT factu, client, datee, montant 
                    FROM infov 
                    WHERE type_fact = ? AND (statut_piece != 'Validé' OR statut_piece ='Validée' ) AND (statut_piece ='En cours' OR statut_piece='Brouillon')
                """, (type_piece,))
                lignes = cur.fetchall()

                for row_num, ligne in enumerate(lignes):
                    self.table.insertRow(row_num)

                    # Case à cocher
                    chk = QCheckBox()
                    widget = QWidget()
                    lay = QHBoxLayout(widget)
                    lay.addWidget(chk)
                    lay.setAlignment(chk, Qt.AlignmentFlag.AlignCenter)
                    lay.setContentsMargins(0, 0, 0, 0)
                    self.table.setCellWidget(row_num, 0, widget)

                    # Infos
                    for col, val in enumerate(ligne):
                        self.table.setItem(row_num, col + 1, QTableWidgetItem(str(val)))

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors du chargement des pièces : {e}")

    
    def valider_selection(self):
        type_piece = self.combo_type.currentText()
        nouveau_statut = self.combo_statut.currentText()

        if type_piece != "Selectionner le Type de Pièce":
            if nouveau_statut != "Selectionner le Statut":
                #try:
                    
                if nouveau_statut not in ["Validé","Annulée","Validée"]:
                    QMessageBox.warning(self, "Action refusée", "Vous ne pouvez valider que les pièces en cours.")
                    return
                with sq.connect(self.db_path) as conn:
                    cur = conn.cursor()
                    total_validees = 0

                    for row in range(self.table.rowCount()):
                        widget = self.table.cellWidget(row, 0)
                        chk = widget.findChild(QCheckBox) if widget is not None else None
                        if chk and chk.isChecked():
                            item = self.table.item(row, 1)
                            if item:
                                num_piece = item.text()
                                # ⚡ Validation métier complète
                                self.validator.execute(num_piece,self.user,nouveau_statut)
                                total_validees += 1

                    conn.commit()
                    self.charger_pieces()
                    QMessageBox.information(self, "Succès", f"{total_validees} pièce(s) mise(s) à jour avec le statut : {nouveau_statut}")

                # except Exception as e:
                #     QMessageBox.critical(self, "Erreur", f"Erreur lors de la validation : {e}")
            else:
                 QMessageBox.warning(self, "Validation", "Veuillez choisir un statut valide.")
        else:
            QMessageBox.warning(self, "Validation", "Veuillez choisir un type de pièce.")            


from PySide6.QtWidgets import QFileDialog
import os

def get_pdf_directory(parent, conn):
    cur = conn.cursor()
    # 🔹 Lire config
    cur.execute("SELECT valeur FROM dossier WHERE cle='PDF_DIR'")
    row = cur.fetchone()

    if row and os.path.isdir(row[0]):
        return row[0]

    # 🔹 Sinon demander à l'utilisateur
    dossier = QFileDialog.getExistingDirectory(
        parent,
        "Choisir le dossier de sauvegarde des PDF"
    )

    if not dossier:
        return None

    # 🔹 Sauvegarder choix
    cur.execute("""
        INSERT OR REPLACE INTO dossier (cle, valeur)
        VALUES ('PDF_DIR', ?)
    """, (dossier,))
    conn.commit()

    return dossier
