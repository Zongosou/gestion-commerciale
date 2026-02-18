import datetime
from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtCore import QDate
from PySide6.QtGui import QIcon
from decimal import Decimal,InvalidOperation
from interface.credit_ui import Ui_Ui_payereste
from fonction.methode import cal
import logging
# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class PaiementResteController(QDialog):
    def __init__(self, db_path,user,facture_data, service_compta=None, parent=None):
        super().__init__(parent)

        self.ui = Ui_Ui_payereste()
        self.ui.setupUi(self)
        self.setWindowIcon(QIcon(":/icon/icone.png"))
        self.cal = cal()
        self.user = user
        self.facture = facture_data
        self.service = service_compta
        self.db = db_path

        # Conversion en Decimal pour Ã©viter erreurs float
        self.reste_initial =self.safe_decimal(str(self.facture["reste"]))

        self._charger_infos_facture()
        self._connect_signals()

    # -----------------------------
    # Chargement des infos facture
    # -----------------------------
    def _charger_infos_facture(self):

        self.ui.numeroFactureLineEdit.setText(str(self.facture["numero"]))
        self.ui.dateLineEdit.setText(str(self.facture["date"]))
        self.ui.montantTotalLineEdit.setText(f'{self.facture["montant_ht"]:,.2f}')
        self.ui.lineEdit.setText(f'{self.facture["montant_ttc"]:,.2f}')
        self.ui.montantPayLineEdit.setText(f'{self.facture["montant_paye"]:,.2f}')
        self.ui.montantRestantLineEdit.setText(f'{self.reste_initial:,.2f}')
        self.ui.label_4.setText(self.facture["statut"])
        self.ui.label_9.setText(self.facture["client"])
        # SÃ©curisation du spinbox
        self.ui.reglELeResteSpinBox.setDecimals(2)
        self.ui.reglELeResteSpinBox.setMaximum(float(self.reste_initial))
        self.ui.reglELeResteSpinBox.setValue(float(self.reste_initial))

        self.ui.dateEdit.setDate(QDate.currentDate())

        # Si dÃ©jÃ  payÃ© â†’ on bloque
        if self.reste_initial <= 0:
            self.ui.pushButton.setEnabled(False)
            QMessageBox.information(
                self,
                "Information",
                "Cette facture est déjà totalement payée."
            )

    # -----------------------------
    # Connexions
    # -----------------------------
    def _connect_signals(self):
        self.ui.comboBox.activated.connect(lambda: self.type_paiement())
        self.ui.pushButton.clicked.connect(lambda: self.handle_unpaid_invoice_payment())
        self.ui.reglELeResteSpinBox.valueChanged.connect(lambda: self.mise_statut())
       
    # -----------------------------
    # Netoyer avant de convertir
    # -----------------------------
    def safe_decimal(self,value):
        try:
            if value is None:
                return Decimal("0")
            # enlever espece et virgule
            clean = str(value).replace("","").replace(",", "")
            return Decimal(clean)
        except (InvalidOperation, ValueError):
            return Decimal("0")
    
   
# ===============================
# --- GESTION PAIEMENT FACTURE IMPAYEE ---
# ===============================
    def handle_unpaid_invoice_payment(self):
        """
        Traite le paiement d'une facture en tenant compte :
        - des paiements précédents
        - des avoirs
        - du solde réel
        - du trop-perçu
        """
        conn = self.cal.connect_to_db(self.db)
        if conn is None:
            QMessageBox.critical(
                self,
                "Erreur de connexion",
                "Impossible de se connecter  la base de données."
            )
            return

        try:
            cur = conn.cursor()

            # -------------------------------------------------
            # Données interface
            # -------------------------------------------------
            invoice_number = self.ui.numeroFactureLineEdit.text().strip()
            payment_amount = Decimal(str(self.ui.reglELeResteSpinBox.value()))
            date_operation = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            num_reference = self.ui.label.text().strip()
            numero_compte = self.ui.comboBox.currentText()
           
            if not invoice_number:
                QMessageBox.warning(self, "Paiement", "Numéro de facture vide.")
                return

            if payment_amount <= 0:
                QMessageBox.warning(self, "Paiement", "Montant invalide.")
                return

            # -------------------------------------------------
            # Charger la facture
            # -------------------------------------------------
            cur.execute("""
                SELECT mnt_ttc, COALESCE(payer, 0), statut_paiement
                FROM infov
                WHERE factu = ? AND type_fact = 'Facture'
            """, (invoice_number,))
            row = cur.fetchone()

            if not row:
                QMessageBox.warning(self, "Erreur", "Facture introuvable.")
                return

            montant_facture, deja_paye_, statut_facture = row
            montant_facture = Decimal(str(abs(montant_facture)))
            deja_paye = Decimal(str(deja_paye_))

            # -------------------------------------------------
            # Blocage si facture non payable
            # -------------------------------------------------
            if statut_facture in ("ANNULEE", "SOLDEE", "TROP-PERCU","PAYEE"):
                QMessageBox.information(
                    self,
                    "Paiement",
                    "Cette facture ne peut plus être réglée."
                )
                return

            # -------------------------------------------------
            # Total des avoirs
            # -------------------------------------------------
            cur.execute("""
                SELECT COALESCE(SUM(mnt_ttc), 0)
                FROM infov
                WHERE origine = ? AND type_fact = 'AVOIR'
            """, (invoice_number,))
            total_avoirs = Decimal(str(abs(cur.fetchone()[0])))

            # -------------------------------------------------
            # Calcul du solde avant paiement
            # -------------------------------------------------
            reste_avant = montant_facture - deja_paye - total_avoirs

            if reste_avant <= 0:
                QMessageBox.information(
                    self,
                    "Paiement",
                    "Aucun paiement requis (avoir ou paiement déjà suffisant)."
                )
                return

            # -------------------------------------------------
            # Vérifier si le paiement dépasse le reste
            # -------------------------------------------------
            if payment_amount > reste_avant:
                reply = QMessageBox.question(
                    self,
                    "Paiement",
                    f"Le paiement de {payment_amount:,.2f} dépasse le reste à payer "
                    f"({reste_avant:,.2f}). Voulez-vous continuer et enregistrer un trop-perçu ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    QMessageBox.information(self, "Paiement", "Paiement annulé.")
                    return

            # -------------------------------------------------
            # Confirmation utilisateur
            # -------------------------------------------------
            reply = QMessageBox.question(
                self,
                "Confirmation",
                f"Confirmez-vous le paiement de {payment_amount:,.2f} "
                f"pour la facture {invoice_number} ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                QMessageBox.information(self, "Paiement", "Paiement annulé.")
                return

            # -------------------------------------------------
            # Nouveau solde aprÃ¨s paiement
            # -------------------------------------------------
            nouveau_paye = deja_paye + payment_amount
            reste_apres = montant_facture - nouveau_paye - total_avoirs

            if reste_apres > 0:
                new_status = "PARTIELLE"
            elif reste_apres == 0:
                new_status = "PAYEE"
            else:
                new_status = "TROP-PERCU"

            conn.execute("BEGIN IMMEDIATE")

            # -------------------------------------------------
            # Mise Ã  jour facture
            # -------------------------------------------------
            cur.execute("""
                UPDATE infov
                SET payer = ?,
                    monn = ?,
                    statut_paiement = ?
                WHERE factu = ? AND type_fact = 'Facture'
            """, (float(nouveau_paye), float(reste_apres), new_status, invoice_number))

            # -------------------------------------------------
            # TrÃ©sorerie
            # -------------------------------------------------
            # try:
            self.cal.insert_tresorerie(
                    cur=cur,
                    date_op=date_operation,
                    libelle="Règlement " + invoice_number,
                    montant=float(payment_amount),
                    type_op="ENTREE",
                    compte=numero_compte,
                    num=num_reference,
                    current_user=self.user
                )
           
            # -------------------------------------------------
            # Commit et retour utilisateur
            # -------------------------------------------------
            conn.commit()
            QMessageBox.information(
                self,
                "Paiement",
                "Paiement enregistré avec succès."
            )
            self.close()

        except Exception as e:
            conn.rollback()
            log.error(f"Erreur paiement: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Erreur",
                f"Une erreur est survenue : {e}"
            )

        finally:
            try:
                conn.close()
            except Exception:
                pass

    # ===============================
# --- MISE A JOUR STATUT ---
# ===============================
    def mise_statut(self):
        try:
            payle = Decimal(str(self.ui.reglELeResteSpinBox.value()))
            reste = Decimal(str(self.ui.montantRestantLineEdit.text()))
            mnt = Decimal(str(self.ui.lineEdit.text()))
            if (reste - payle) == 0.0 or payle > mnt:
                self.ui.label_4.setText("SOLDEE")
                self.ui.label_4.setStyleSheet("background-color:green;color:white;")
            elif payle == 0.0:
                self.ui.label_4.setText("Impayé")
            elif (reste - payle) < 0:
                self.ui.label_4.setText("SOLDEE")
                self.ui.label_4.setStyleSheet("background-color:green;color:white;")
            else:
                self.ui.label_4.setText("Avance")
                self.ui.label_4.setStyleSheet("background-color:blue;color:white;")
        except Exception as e:
            log.error(f"Erreur mise_statut: {e}", exc_info=True)


# ===============================
# --- TYPE PAIEMENT ---
# ===============================
    def type_paiement(self):
        moyen_paiem = self.ui.comboBox.currentText()
        moyen = self.cal.code_paiement(moyen_paiem)
        facture = self.ui.numeroFactureLineEdit.text()
        moyen_ = f"{moyen}-{facture}"
        self.ui.label.setText(moyen_)




