# auteur: zongo soumaÃ¯la
# Tel: +226 54267778 / 70925613

import os
import datetime
from openpyxl import Workbook
import pandas as pd
from PySide6.QtCore import QSize, Qt, QDate
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QFileDialog, QStyle, QTableView, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel,
    QComboBox, QDateEdit, QTableWidget,
    QTableWidgetItem,QToolBar,
    QMessageBox, QMenu, QFrame
)

from caisse.TresorerieDash import RapportManager
from fonction.methode import cal
from fonction.model import Model
from piece.avoirService import AvoirService
from piece.paiement import PaiementResteController
from vente.creepiece import Vente
from piece.compl import DialogueConversion, ValidationPieces, get_pdf_directory

from piece.avoir_dialog import AvoirDialog
from stock.gest_stock import SummaryCard
import logging

from vente.models.piece_model import PieceTableModel

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class ListePiece(QWidget):

    # =====================================================
    # INIT
    # =====================================================
    def __init__(self, dbfolder: str, user=None):
        super().__init__()
        self.dbfolder = dbfolder
        self.user = user
        self.setWindowIcon(QIcon(":/icon/icone.png"))

        self.cal = cal()
        self.Model = Model()
        self.manager = RapportManager(self.dbfolder)
        self.serviceAvoir = AvoirService(self.dbfolder, self.user)
        self.current_sort_column = "datee"
        self.current_sort_order = "DESC"
        self.page_size = 50
        self.current_page = 0
        self.cols = [
            "N°Facture", "ID Client", "Mnt HT", "Mnt TTC",
            "Mnt versé", "Mnt restant", "Statut pièce","Etat paiement",
            "Date", "Pièce", "Source", "Users"
        ]

        (
            self.COL_FACTURE, self.COL_CLIENT, self.COL_MONTANT_HT,
            self.COL_MONTANT_TTC, self.COL_VERSE, self.COL_RESTANT,
            self.COL_STATUT_PIECE, self.COL_ETAT_PAIEMENT, self.COL_DATE, self.COL_PIECE,
            self.COL_SOURCE, self.COL_USER
        ) = range(len(self.cols))

        self.full_rows = []
        self.cached_data = []
        self.create_actions()
        self.create_toolbar()
        self.ini()
        self._update_summary_cards(
            total_products=self.manager.ca_total(),
            low_stock_alerts=self.manager.nb_factures(),
            total_value=self.manager.panier_moyen()
        )
       
    # =====================================================
    # BOUTON GÃ‰NÃ‰RIQUE
    # =====================================================
    def create_button(self, text, icon, tooltip, callback, style="PrimaryButton"):
        btn = QPushButton(text)
        btn.setIcon(QIcon(icon))
        btn.setToolTip(tooltip)
        btn.setObjectName(style)
        btn.clicked.connect(callback)
        return btn

   
    # =====================================================
    # UI PRINCIPALE
    # =====================================================
    def ini(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.top_toolbar)
        layout.addWidget(self.ribbon_toolbar)
        
        # self.toolbar = self.create_toolbar()
        # layout.setSpacing(2)
        # layout.addWidget(self.toolbar)
        # ================= CARTES =================
        cards_row = QHBoxLayout()

        self.card_total = SummaryCard("Chiffres d'Affaires (CA)", "0.0", accent="#2D7EF7")
        self.card_alerts = SummaryCard("Nombre de Factures", "0.0", accent="#F59E0B")
        self.card_value = SummaryCard("Panier Moyen", "0.0", accent="#10B981")
        self.card_marge = SummaryCard("Marge Totale", "0.0", accent="#8B5CF6")
        
        for card in (self.card_total, self.card_alerts, self.card_value,self.card_marge):
            cards_row.addWidget(card, 1)

        layout.addLayout(cards_row)
        # ---------- TABLE ----------
        self.table = QTableView()
        self.model = PieceTableModel([])
        self.table.setModel(self.model)
        self.table.doubleClicked.connect(self.open_selected_piece)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)

        # Connexion sélection
        self.table.selectionModel().selectionChanged.connect(
            self.update_actions_state
        )
        self.table.horizontalHeader().sectionClicked.connect(
    self.handle_header_click
)
        self.table.setFrameShape(QFrame.Shape.Box)
        self.table.setColumnWidth(self.COL_FACTURE, 150)
        self.table.setColumnWidth(self.COL_CLIENT, 100)
        self.table.setColumnWidth(self.COL_MONTANT_HT, 120)
        self.table.setColumnWidth(self.COL_MONTANT_TTC, 120)
        self.table.setColumnWidth(self.COL_VERSE, 120)
        self.table.setColumnWidth(self.COL_RESTANT, 120)
        self.table.setColumnWidth(self.COL_STATUT_PIECE, 130)
        self.table.setColumnWidth(self.COL_ETAT_PAIEMENT, 130)
        self.table.setColumnWidth(self.COL_DATE, 150)
        self.table.setColumnWidth(self.COL_PIECE, 130)
        self.table.setColumnWidth(self.COL_SOURCE, 130)
        self.table.setColumnWidth(self.COL_USER, 150)

        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)

        # ---------- SIGNALS ----------
        # self.search.textChanged.connect(self.filter_local)
        # self.liste_pice.currentTextChanged.connect(self.filter_pice)
        self.date_debut.dateChanged.connect(self.refresh)
        self.date_fin.dateChanged.connect(self.refresh)
        self.refresh()
    
    # =====================================================
    # UTILITAIRE ICONES
    # =====================================================
    def icon(self, name):
        base_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon")
        return QIcon(os.path.join(base_path, f"{name}.svg"))
    # ===============================
    # --- ACTIONS ---
    # ===============================
    def create_actions(self):
        self.act_add = QAction(QIcon(":icon/ajouter.png"), "Nouvelle Pièce", self,toolTip="Créer une nouvelle pièce")
        self.act_add.setShortcut("Ctrl+N")
        self.act_add.triggered.connect(self.open_window)

        self.act_validate = QAction(QIcon(":icon/update.png"), "Valider une Pièce", self,toolTip="Valider la pièce sélectionnée")
        self.act_validate.triggered.connect(self.open_liste_valide)

        self.act_transform = QAction(QIcon(":icon/subscription-model.png"), "Transformer", self,toolTip="Transformer la pièce sélectionnée en d'autre pièce")
        self.act_transform.triggered.connect(self.open_conver)

        self.act_pay = QAction(QIcon(":icon/caisse-enregistreuse.png"), "Paiment Facture", self,toolTip="Enregistrer un paiement pour la facture sélectionnée")
        self.act_pay.triggered.connect(self.paiement)

        self.act_print = QAction(QIcon(":icon/telecharger-le-pdf.png"), "Exporter en PDF", self,toolTip="Exporter la pièce sélectionnée en PDF")
        self.act_print.setShortcut("Ctrl+P")
        self.act_print.triggered.connect(self.facture_generate)
        self.act_export = QAction(QIcon(":icon/xls.png"), "Exporter Excel", self,toolTip="Exporter la liste des pièces affichées vers Excel")
        self.act_export.triggered.connect(self.export_excel)
        

        self.act_delete = QAction(QIcon(":icon/delete.png"), "Supprimer", self,toolTip="Supprimer la pièce sélectionnée")
        self.act_delete.setShortcut("Del")
        self.act_delete.triggered.connect(self.delete_fact_vent)

        self.act_refresh = QAction(QIcon(":icon/refresh.png"), "Actualiser", self,toolTip="Rafraîchir la liste des pièces")
        self.act_refresh.setShortcut("F5")
        self.act_refresh.triggered.connect(self.refresh)

        self.act_avoir = QAction(QIcon(":icon/238.png"), "Créer un Avoir", self,toolTip="Créer un avoir à partir de la facture sélectionnée")
        self.act_avoir.triggered.connect(self.creer_avoir_depuis_facture_a)

        self.act_prev = QAction(QIcon.fromTheme("go-previous", self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)), "Précédent", self, toolTip="Page précédente")
        self.act_prev.triggered.connect(lambda: self.change_page(-1))

        self.act_next = QAction(QIcon.fromTheme("go-next",), "Suivant", self, toolTip="Page suivante")
        self.act_next.triggered.connect(lambda: self.change_page(1))

        # Aliases used in the ribbon toolbar labels.
        self.act_new = self.act_add
        self.act_edit = self.act_transform

    
    # ===============================
    # --- TOOLBAR ---
    # ===============================
    def create_toolbar(self):
        
        top_toolbar = QToolBar("Navigation", self)
        top_toolbar.setMovable(False)
        self.top_toolbar = top_toolbar

        top_toolbar.addAction(self.act_prev)
        top_toolbar.addAction(self.act_next)

        top_toolbar.addSeparator()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Rechercher facture ou client...")
        self.search_edit.setFixedWidth(200)
        self.search_edit.returnPressed.connect(self.apply_filters)
        
        top_toolbar.addWidget(self.search_edit)
        top_toolbar.addSeparator()
        self.liste_pice = QComboBox()
        self.liste_pice.addItems(["Pièce", "Devis", "Commande","Bon de livraison", "Facture"])
        self.liste_pice.activated.connect(self.apply_filters)
        top_toolbar.addWidget(self.liste_pice)

        self.date_debut = QDateEdit(QDate.currentDate())
        self.date_fin = QDateEdit(QDate.currentDate())
        for d in (self.date_debut, self.date_fin):
            d.setCalendarPopup(True)
            d.setDisplayFormat("yyyy-MM-dd")
        top_toolbar.addWidget(QLabel("Du"))
        top_toolbar.addWidget(self.date_debut)
        top_toolbar.addWidget(QLabel("Au"))
        top_toolbar.addWidget(self.date_fin)
        
        ribbon_toolbar = QToolBar("Actions", self)
        ribbon_toolbar.setMovable(False)
        ribbon_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        ribbon_toolbar.setIconSize(QSize(24, 24))
        self.ribbon_toolbar = ribbon_toolbar

        # Groupe 1
        ribbon_toolbar.addAction(self.act_new)
        ribbon_toolbar.addAction(self.act_validate)
        ribbon_toolbar.addAction(self.act_transform)
        ribbon_toolbar.addAction(self.act_edit)
        ribbon_toolbar.addAction(self.act_delete)
        ribbon_toolbar.addSeparator()

        # Groupe 2
        ribbon_toolbar.addAction(self.act_pay)
        ribbon_toolbar.addAction(self.act_avoir)
        ribbon_toolbar.addSeparator()

        # Groupe 3
        ribbon_toolbar.addAction(self.act_print)
        ribbon_toolbar.addAction(self.act_export)
        
        

    def change_page(self, delta):
        next_page = max(0, self.current_page + delta)
        if next_page == self.current_page:
            return
        self.current_page = next_page
        self.refresh()
   
# ===============================
# --- CONTEXT MENU ---
# =============================== 
    def show_context_menu(self, pos):
        if not self.table.currentIndex().isValid():
            return
        menu = QMenu(self)
        menu.addAction(self.act_pay)
        menu.addAction(self.act_print)
        menu.addAction(self.act_export)
        menu.addSeparator()
        menu.addAction(self.act_delete)
        menu.addSeparator()
        menu.addAction(self.act_avoir)
        menu.exec(self.table.viewport().mapToGlobal(pos))


# ===============================
# --- UPDATE ACTIONS STATE ---
# ===============================
    def update_actions_state(self):
      
        indexes = self.table.selectionModel().selectedRows()

        has_selection = len(indexes) > 0
        
        self.act_validate.setEnabled(has_selection)
        self.act_transform.setEnabled(has_selection)
        self.act_pay.setEnabled(has_selection)
        self.act_print.setEnabled(has_selection)
        self.act_delete.setEnabled(has_selection)
        self.act_avoir.setEnabled(has_selection)


# ===============================
# --- UPDATE SUMMARY CARDS ---
# ===============================
    def _update_summary_cards(self, total_products, low_stock_alerts, total_value):
        
        # Update labels inside cards
        self.card_total.findChild(QLabel, "SummaryValue").setText(str(total_products))
        self.card_alerts.findChild(QLabel, "SummaryValue").setText(str(low_stock_alerts))
        self.card_value.findChild(QLabel, "SummaryValue").setText(self.cal.separateur_milieur(total_value))
        marge_totale = self.manager.marge_totale()
        self.card_marge.findChild(QLabel, "SummaryValue").setText(
                                    self.cal.separateur_milieur(marge_totale)
                                )


    # =====================================================
    # ACTIONS BOUTONS
    # =====================================================
    def open_window(self):
        # self.vente = Vente()
        # self.vente.show()
        Vente(self.dbfolder, current_user=self.user).show()
        

    def open_liste_valide(self):
        ValidationPieces(self.dbfolder,self.user).exec()

    def open_conver(self):
        DialogueConversion(self.dbfolder, self.user).exec()

   
    # =====================================================
    # OBTENIR TOUTES LES PIECES AVEC FILTRE DE RECHERCHE
    # =====================================================
    def get_all_pice(self, search_text=""):

        conn = self.cal.connect_to_db(self.dbfolder)
        cur = conn.cursor()

        query = """
            SELECT factu, client, montant, mnt_ttc,
                payer, monn, statut_paiement,
                statut_piece, utilisateur, datee,
                type_fact
            FROM infov
        """

        params = []

        # 🔎 FILTRE
        if search_text:
            query += """
            WHERE factu LIKE ?
            OR client LIKE ?
            """
            params.extend([f"%{search_text}%", f"%{search_text}%"])

        # 📊 TRI + PAGINATION
        query += f"""
        ORDER BY {self.current_sort_column} {self.current_sort_order}
        LIMIT ? OFFSET ?
        """

        offset = self.current_page * self.page_size
        params.extend([self.page_size, offset])
        
        # 🔥 EXECUTION (c'était ça qui manquait)
        cur.execute(query, params)

        data = cur.fetchall()

        conn.close()
        return data

    # =====================================================
    # GESTION TRI PAR CLIQUE SUR HEADER
    # =====================================================
    def handle_header_click(self, logical_index):

        columns_map = {
            0: "factu",
            1: "client",
            2: "montant",
            3: "mnt_ttc",
            4: "payer",
            5: "monn",
            6: "statut_paiement",
            7: "utilisateur",
            8: "datee"
        }

        col_name = columns_map.get(logical_index)
        if not col_name:
            return

        if self.current_sort_column == col_name:
            self.current_sort_order = (
                "ASC" if self.current_sort_order == "DESC" else "DESC"
            )
        else:
            self.current_sort_column = col_name
            self.current_sort_order = "ASC"

        self.refresh()

    # ===============================
    # --- RAFFRAICHIR TABLE ---
    # ===============================
    def refresh(self):
        search = self.search_edit.text().strip()
        data = self.get_all_pice(search)
        self.model.update_data(data)
        self.update_actions_state()

    # =====================================================
    # FILTRES
    # =====================================================
    # def filter_local(self, text):
    #     t = text.lower()
    #     self.table.setRowCount(0)
    #     for row in self.full_rows:
    #         if any(t in str(v).lower() for v in row):
    #             r = self.table.rowCount()
    #             self.table.insertRow(r)
    #             for c, val in enumerate(row):
    #                 self.table.setItem(r, c, QTableWidgetItem(str(val)))

    # def filter_pice(self, text):
    #     self.table.setRowCount(0)
    #     for row in self.full_rows:
    #         if not text or text.lower() in str(row[self.COL_PIECE]).lower():
    #             r = self.table.rowCount()
    #             self.table.insertRow(r)
    #             for c, val in enumerate(row):
    #                 self.table.setItem(r, c, QTableWidgetItem(str(val)))
   
    def apply_filters(self):
        if hasattr(self, "search_edit"):
            search = self.search_edit.text().strip()
        else:
            search = self.search.text().strip()
        data = self.get_all_pice(search)
        self.model.update_data(data)
    
# ===============================
# --- SUPPRIMER PIECES ---
# ===============================
    def delete_fact_vent(self):
        """
        Supprime une ou plusieurs factures sÃ©lectionnÃ©es dans la QTableView.
        """
        con = self.cal.connect_to_db(self.dbfolder)
        if con is None:
            return
        cur = con.cursor()

        indexes = self.table.selectedIndexes()
        if not indexes:
            QMessageBox.warning(self, "Suppression", "Aucun élement sélectionné. Veuillez sélectionner une ou plusieurs lignes!")
            con.close()
            return
        rows = {index.row() for index in indexes}
        ids_to_delete = []
        try:
            model = self.table.model()
            if model is None:
                con.close()
                return

            for row in rows:
                id_index = model.index(row, self.COL_FACTURE)
                type_fact_index = model.index(row, self.COL_PIECE)

                facture_id = model.data(id_index)
                facture_type = model.data(type_fact_index)

                ids_to_delete.append({'id': facture_id, 'type': facture_type})

        except Exception as e:
            log.error(f"Une erreur est survenue lors de la recupération des données de sélection : {str(e)}", exc_info=True)
            QMessageBox.information(self, "Erreur", f"Une erreur est survenue lors de la récupération des données de sélection : {str(e)}")
            con.close()
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("SUPPRESSION")
        msg.setText(f"Êtes-vous sûr de vouloir supprimer les données de ces {len(ids_to_delete)} pièces?")
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Voulez-vous continuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                con.execute("BEGIN IMMEDIATE")
                for item in ids_to_delete:
                    facture_id = item['id']
                    facture_type = item['type']
                    sql1 = "DELETE FROM vent WHERE facture = ?" if facture_type in ["Facture", "Ticket"] else "DELETE FROM liste WHERE facture = ?"
                    cur.execute(sql1, (facture_id,))
                    cur.execute("DELETE FROM infov WHERE factu=?", (facture_id,))
                    cur.execute("SELECT monn FROM infov WHERE factu=?", (facture_id,))
                    reste_check = cur.fetchone()

                    if reste_check and float(reste_check[0]) != 0:
                        QMessageBox.warning(
                            self,
                            "Suppression impossible",
                            "Impossible de supprimer une facture non soldée."
                        )
                        continue
                con.commit()
                QMessageBox.information(self, "Succès", f"Les {len(ids_to_delete)} pièces ont été supprimées avec succès.")
            except Exception as e:
                con.rollback()
                log.error(f"Erreur suppression pièces: {e}", exc_info=True)
                QMessageBox.critical(self, "Erreur", f"Impossible de supprimer les pièces: {e}")
        else:
            con.rollback()
            QMessageBox.information(self, "Annulation", "La suppression a été annulée.")
        con.close()

    # utilitaire pour obtenir la valeur de la cellule sÃ©lectionnÃ©e
    def _selected_row_value(self, col_index):
        model = self.table.model()
        index = self.table.currentIndex()
        if model is None or not index.isValid():
            return None
        row = index.row()
        idx = model.index(row, col_index)
        if not idx.isValid():
            return None
        return model.data(idx)
    
    def paiement(self):
        invoice_id = str(self._selected_row_value(self.COL_FACTURE))
        if invoice_id is None:
            QMessageBox.warning(self, "Paiement", "Aucun élement sélectionné. Veillez sélectionner une ligne!")
            return
        # Récupérer la facture complète depuis la base
        
        facture_data = self.get_facture_by_id(invoice_id)

        if not facture_data:
            QMessageBox.warning(self, "Paiement", "Facture introuvable en base.")
            return
        if facture_data["type_fact"] != "Facture":
            QMessageBox.warning(self, "Paiement", f"Paiement impossible pour {facture_data['type_fact']}.")
            return
        
        if facture_data["statut"] in ["PAYEE", "SOLDE"]:
            QMessageBox.information(self, "Paiement", "Cette facture est déjà soldée.")
            return
        if facture_data["valide"] in ["Brouillon"]:
            QMessageBox.information(self, "Paiement", "Cette facture n'est pas validée.")
            return

        dialog = PaiementResteController(
            db_path=self.dbfolder,
            user=self.user,
            facture_data=facture_data,
            # service_compta=self.service_compta,
            parent=self
        )

        dialog.exec()
        
        #  RafraÃ®chir tableau aprÃ¨s paiement
        self.refresh()

        
    

    def get_facture_by_id(self,factu_id:str):
        conn = self.cal.connect_to_db(self.dbfolder)
        if conn is None:
            return
        cur = conn.cursor()
        sql = 'SELECT * FROM infov WHERE factu=?'
        cur.execute(sql, (factu_id,))
        res = cur.fetchone()
        if res:
            return {
                "id":res[0],
                "numero":res[1],
                "date":res[8],
                "montant_ht":res[3],
                "montant_ttc":res[4],
                "montant_paye":res[5],
                "reste":res[6],
                "statut":res[9],
                "client":res[2],
                "type_fact":res[8],
                "valide":res[10]
            }
        return None

# ===============================
# --- IMPRIMER UN DOCUMENT ---
# ===============================
    
    def liste_article(self):
        conn = self.cal.connect_to_db(self.dbfolder)
        if conn is None:
            log.error("Database connection failed in liste_article()")
            return []
        try:
            cur = conn.cursor()
            index = self.table.currentIndex()
            model = self.table.model()
            if model is None or not index.isValid():
                log.error("No model or invalid index in liste_article()")
                return []
            nindex = model.index(index.row(), self.COL_FACTURE)
            va = model.data(nindex)
            type_fact_index = model.index(index.row(), self.COL_PIECE)
            type_fact = model.data(type_fact_index)
            sql = "SELECT libelle, quantite,prix,montant FROM "
            if type_fact == "Facture":
                sql += "vent where facture =?"
                cur.execute(sql, (va,))
            else:
                sql += "liste where facture =?"
                cur.execute(sql, (va,))
            res = cur.fetchall()
            Data = []
            for item in res:
                if item not in Data:
                    Data.append(item)
            return Data
        except Exception as e:
            log.error(f"Erreur liste_article: {e}", exc_info=True)
            return []
        finally:
            try:
                conn.close()
            except Exception:
                pass
    
    # =====================================================
    # OUVRIR LA FENETRE DE LA PIECE SELECTIONNEE
    # =====================================================
    def open_selected_piece(self, index):
        if not index.isValid():
            return

        row = index.row()
        piece = self.model.get_row(row)

        if not piece:
            return

        facture_id = piece[0]
        type_piece = piece[9]

        self.open_window(facture_id, type_piece)
# ===============================
# --- Information sur une piece ---
# ===============================
    def Info(self):
        try:
            var_dic_vente = {}
            self.date = "_"
            self.facto = "_"
            self.montant_verse = 0.0
            self.reste = 0.0
            self.nom_clt = "Client ordinaire"
            self.contact1 = "_"
            self.adresse1 = "_"
            self.type_fact = ""
            self.ville = "_"
            conn = self.cal.connect_to_db(self.dbfolder)
            if conn is None:
                return
            cur = conn.cursor()
            index = self.table.currentIndex()
            nindex = self.table.model()
            if nindex is None or not index.isValid():
                return
            va = self._selected_row_value(self.COL_FACTURE)
            if va is None:
                return
            pr_v = 'SELECT * from infov where factu=?'
            cur.execute(pr_v, [va])
            cv = cur.fetchone()
            if cv:
                # protections d'index
                self.date = cv[7] if len(cv) > 7 and cv[7] else "_"
                self.facto = cv[1]
                self.montant_verse = cv[5]
                self.reste = cv[6]
                self.type_fact = cv[8] if len(cv) > 8 and cv[8] else ""
                self.remarque = cv[13] if len(cv) > 13 and cv[13] else ""
            info = 'SELECT nom,cont,adr,ville from client where id=?'
            cur.execute(info, [cv[2] if cv else None])
            info_clt = cur.fetchone()
            if info_clt:
                self.nom_clt = info_clt[0]
                self.contact1 = info_clt[1]
                self.adresse1 = info_clt[2]
                self.ville = info_clt[3]
            date_obj = datetime.datetime.strptime(self.date, "%Y-%m-%d %H:%M:%S")
            self.date_formatee = date_obj.strftime("%d %B %Y")
            
            var_dic_vente = {
                "Adrresse": self.adresse1,
                "Contact": self.contact1,
                "date":self.date_formatee ,
                "facture": self.facto,
                "ville": self.ville,
                "nom": self.nom_clt,
                "mont_verse": self.montant_verse,
                "reste": self.reste,
                "type_facture": self.type_fact,
                "remarque": self.remarque
            }
            return var_dic_vente
        except Exception as e:
            log.error(f"Une erreur est survenue: {str(e)} dans Info", exc_info=True)
            QMessageBox.warning(self, "Erreour", f"{e} dans Info")
            return None
        finally:
            try:
                conn.close()
            except Exception:
                pass
# ===============================
# --- Generer un PDF POUR LE DOCUMENT ---
# ===============================
    def facture_generate(self):
        try:
            conn = self.cal.connect_to_db(self.dbfolder)
            if conn is None:
                return
            cur = conn.cursor()
            vente = self.Info()
            if not vente:
                return
            infoEntrp = self.cal.print_info(self.dbfolder)
            self.tau = self.cal.charger_tva_devise(self.dbfolder)
            if self.tau is None:
                return
            if infoEntrp is None:
                return
            donne = self.liste_article()
            self.logo_chemin = self.cal.get_logo_path(cur)
            self.sig_chemin = self.cal.get_sign_path(cur)
            self.cah_chemin = self.cal.get_cach_path(cur)
            donnees = self.Model.facture_donnees(
                Entr=infoEntrp['nom'],
                T1=infoEntrp['T1'],
                T2=infoEntrp['T2'],
                info=infoEntrp['info'],
                ville=infoEntrp['ville'],
                adresse=infoEntrp['adresse'],
                responsabable=infoEntrp['resp'],
                ifu=infoEntrp['ifu'],
                autre=infoEntrp['autre'],
                list_article=donne,
                vente=vente,
                msg=vente["type_facture"],
                remarque=infoEntrp.get('remarque', []),
                date=datetime.datetime.now().strftime("%d/%m/%Y"),
                chemin=self.logo_chemin,
                sign=self.sig_chemin,
                cahet=self.cah_chemin,
                taux=self.tau.get('tva', 0),
                devise=self.tau.get('devise','')

            )

            pdf_dir = get_pdf_directory(self, conn)
            if not pdf_dir:
                return

            facture_numero = vente['facture']
            pdf_path = os.path.join(pdf_dir, f"{facture_numero}.pdf")
           
            self.Model.generer_facture_pdf_reportlab(donnees, pdf_path)
            rep = QMessageBox(self)
            rep.setWindowTitle("PDF")
            rep.setText("Document généré.\nVoulez-vous l’ouvrir maintenant ?")

            btn_yes = rep.addButton("Oui", QMessageBox.ButtonRole.AcceptRole)
            btn_no = rep.addButton("Non", QMessageBox.ButtonRole.RejectRole)

            rep.exec()
            if rep.clickedButton() == btn_yes:
                self.cal.ouvrir_pdf(pdf_path)
            else:
                return
                
        except Exception as e:
            log.error(e, exc_info=True)
            QMessageBox.critical(self, "Erreur PDF", str(e))
        finally:
            if conn:
                conn.close()

# ===============================
# --- GÃ©nÃ©rer un avoir depuis une facture ---
# ===============================
    def creer_avoir_depuis_facture_a(self):
        index = self.table.currentIndex()
        if not index.isValid():
            QMessageBox.warning(self, "Attention", "Sélectionnez une facture")
            return

        piece_id = str(self._selected_row_value(self.COL_FACTURE))
        type_piece = self._selected_row_value(self.COL_PIECE)
        
        if type_piece != "Facture":
            QMessageBox.warning(self, "Erreur", "Un avoir ne peut venir que d'une facture")
            return

        # ouvrir fenêtre de sélection lignes
        dlg = AvoirDialog(piece_id, self.dbfolder,self)
        if dlg.exec():
            lignes = dlg.get_lignes_avoir()
            self.serviceAvoir.creer_avoir(piece_id, lignes)
            # self._creer_avoir_sql(piece_id, lignes)
            QMessageBox.information(self, "Succès", "Avoir créé avec succès.") 

    # exporter la liste des pièces affichées vers Excel
    def export_excel(self):

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter en Excel",
            "",
            "Excel Files (*.xlsx)"
        )

        if not path:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Liste Factures"

        # Headers
        ws.append(PieceTableModel.HEADERS)

        # Data
        for row in self.model._data:
            ws.append(row)

        wb.save(path)

        QMessageBox.information(self, "Export", "Export réussi !")
