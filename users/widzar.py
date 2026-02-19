import re
import secrets
import shutil
from PySide6.QtWidgets import (
     QDialog, QTabWidget, QWidget,
    QVBoxLayout, QFormLayout,  QLineEdit, QPushButton,
    QDateEdit, QFileDialog, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QMessageBox, QDoubleSpinBox,QGroupBox,QComboBox,QLabel,QSpinBox
)
from PySide6.QtCore import QDate
from PySide6.QtGui import QIcon
from users.permission_editor import PermissionEditor
from users.role_manager import RoleManager

from fonction.methode import cal
from fonction.model import hash_password
import os

CONFIG_FOLDER = "config"

class SetupWizardTabs(QDialog):
    def __init__(self, db_path=None,logo_path=None):
        super().__init__()
        self.setWindowTitle("Configuration initiale")
        self.setWindowIcon(QIcon(":/icon/icone.png"))
        self.resize(600, 400)
        self.db_path = db_path
        self.logo_path = logo_path
        self.cal = cal()
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 8px 15px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #2c3e50;
                color: white;
            }
        """)

        layout.addWidget(self.tabs)

        # === Onglets ===
        self.tab_entreprise = QWidget()
        self.tabs.addTab(self.tab_entreprise, "Entreprise")
        self._init_onglet_entreprise()

        self.tab_exercice = QWidget()
        self.tabs.addTab(self.tab_exercice, "Exercice & Dépôts")
        self._init_onglet_exercice()

        self.tab_users = QWidget()
        self.tab_users.setStyleSheet("""
            QTabBar::tab {
                padding: 6px 12px;
            }
        """)

        self.tabs.addTab(self.tab_users, "Utilisateurs")
        self._init_onglet_users()

        # Bouton final et Bouton d'affichage
        Box_Hor = QHBoxLayout()
        self.btn_save = QPushButton("Enregistrer la configuration")
        self.btn_load = QPushButton("Afficher les données")
        self.btn_save.setIcon(QIcon(":/icon/administration.png"))
        self.btn_save.clicked.connect(self.save_all)
        self.btn_load.clicked.connect(self._ini_onglet_affiche)
        Box_Hor.addWidget(self.btn_save)
        Box_Hor.addWidget(self.btn_load)
        layout.addLayout(Box_Hor)
        self.affiche_config()
        
    def copier_image(self, src, dossier, nom):
        base = self.cal.ensure_assets_dirs()
        dest = os.path.join(base, dossier, nom)
        shutil.copy(src, dest)
        return dest

    def save_param(self, cle, valeur):
        conn = self.cal.connect_to_db(self.db_path)
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO dossier (cle, valeur)
            VALUES (?, ?)
        """, (cle, valeur))
        conn.commit()

    def choisir_image(self, titre):
        fichier, _ = QFileDialog.getOpenFileName(
            self,
            titre,
            "",
            "Images (*.png *.jpg *.jpeg)"
        )
        return fichier if fichier else None
    def load_logo(self):
        f = self.choisir_image("Choisir le logo")
        if f:
            path = self.copier_image(f, "logo", "logo.png")
            self.save_param("logo_path", path)

    def load_cachet(self):
        f = self.choisir_image("Choisir le cachet")
        if f:
            path = self.copier_image(f, "cachet", "cachet.png")
            self.save_param("cachet_path", path)
    def load_sign(self):
        f = self.choisir_image("Choisir la signature")
        if f:
            path = self.copier_image(f, "signature", "signature.png")
            self.save_param("signature_path", path)

    # === Onglet Entreprise ===
    def _init_onglet_entreprise(self):
        form = QFormLayout(self.tab_entreprise)
        self.nom_entreprise = QLineEdit()
        self.tel1 = QLineEdit()
        self.tel2 = QLineEdit()
        self.responsable = QLineEdit()
        self.adresse = QLineEdit();self.adresse.setPlaceholderText("Nom du secteur ou le Numéro")
        self.ville = QLineEdit()
        self.ifu = QLineEdit();self.ifu.setPlaceholderText("IFU-CNSS-RCCM")
        self.autre = QLineEdit();self.autre.setPlaceholderText("Email, Poste, ou autre")
        self.details = QLineEdit();self.details.setPlaceholderText("Information sur votre service")
        
        form.addRow("Nom entreprise:", self.nom_entreprise)
        form.addRow("Détails:",self.details)
        form.addRow("Téléphone:", self.tel1)
        form.addRow("WhatsApp:", self.tel2)
        form.addRow("Responsable:", self.responsable)
        form.addRow("Adresse:", self.adresse)
        form.addRow("Ville:", self.ville)
        form.addRow("IFU:", self.ifu)
        form.addRow("Autres infos:", self.autre)
        
    # === Onglet Exercice ===
    def _init_onglet_exercice(self):
        main_layout = QVBoxLayout(self.tab_exercice)
        form = QFormLayout()

        self.date_debut = QDateEdit(QDate.currentDate())
        self.date_fin = QDateEdit(QDate.currentDate().addYears(1))
        self.devise = QLineEdit("CFA")
        self.tva = QDoubleSpinBox()
        self.tva.setValue(18.0)   
        # Button logo 
        self.btn_load_logo =   QPushButton("📎 Choisir Logo")  
        self.btn_load_logo.clicked.connect(self.load_logo)
        # Button signature 
        self.btn_load_sign =   QPushButton("✍️ Choisir Signature")  
        self.btn_load_sign.clicked.connect(self.load_sign)
        # Button cachet 
        self.btn_load_ch =   QPushButton("🟣 Choisir Cachet")  
        self.btn_load_ch.clicked.connect(self.load_cachet)
        Box_Hor = QVBoxLayout()
        Box_Hor.addWidget(self.btn_load_logo)
        Box_Hor.addWidget(self.btn_load_sign)
        Box_Hor.addWidget(self.btn_load_ch)
        form.addRow("Début exercice:", self.date_debut)
        form.addRow("Fin exercice:", self.date_fin)
        form.addRow("Devise:", self.devise)
        form.addRow("TVA (%):", self.tva)
        main_layout.addLayout(form)
        main_layout.addLayout(Box_Hor)
        # =======================
        # 🔢 Paramétrage Numérotation
        # =======================
        grp_num = QGroupBox("Numérotation des pièces")
        layout_num = QFormLayout(grp_num)

        # Type de pièce
        self.cmb_piece_num = QComboBox()
        self.cmb_piece_num.addItems([
            "Facture", "Avoir", "Bon de livraison", "Devis","Commande"
        ])

        # Préfixe
        self.ed_prefixe = QLineEdit("FAC")

        # Séparateur
        self.cmb_sep = QComboBox()
        self.cmb_sep.addItems(["-", "/", "_"])

        # Longueur compteur
        self.spin_longueur = QSpinBox()
        self.spin_longueur.setRange(2, 6)
        self.spin_longueur.setValue(3)

        # Remise à zéro
        self.cmb_reset = QComboBox()
        self.cmb_reset.addItems(["AUCUN", "ANNUEL", "MENSUEL"])

        # Aperçu
        self.lbl_preview_num = QLabel()
        self.lbl_preview_num.setStyleSheet(
            "font-weight:bold; color:#2a7; background:#f6f6f6; padding:4px"
        )

        # Bouton enregistrer
        self.btn_save_num = QPushButton("💾 Enregistrer la numérotation")
        self.btn_save_num.clicked.connect(self.save_numerotation)

        # Ajout au layout
        layout_num.addRow("Type de pièce :", self.cmb_piece_num)
        layout_num.addRow("Préfixe :", self.ed_prefixe)
        layout_num.addRow("Séparateur :", self.cmb_sep)
        layout_num.addRow("Longueur compteur :", self.spin_longueur)
        layout_num.addRow("Remise à zéro :", self.cmb_reset)
        layout_num.addRow("Aperçu :", self.lbl_preview_num)
        layout_num.addRow("", self.btn_save_num)

        # Mise à jour aperçu en live
        self.cmb_piece_num.currentIndexChanged.connect(self.update_preview_num)
        self.ed_prefixe.textChanged.connect(self.update_preview_num)
        self.cmb_sep.currentIndexChanged.connect(self.update_preview_num)
        self.spin_longueur.valueChanged.connect(self.update_preview_num)
        self.cmb_reset.currentIndexChanged.connect(self.update_preview_num)
        self.cmb_piece_num.currentIndexChanged.connect(self.charger_numerotation)


        # Ajouter au layout principal
        main_layout.addWidget(grp_num)

        # Aperçu initial
        self.update_preview_num()
    def update_preview_num(self):
        an = QDate.currentDate().year()
        mois = QDate.currentDate().month()

        prefixe = self.ed_prefixe.text().strip()
        sep = self.cmb_sep.currentText()
        lg = self.spin_longueur.value()

        preview = f"{prefixe}{sep}{an}{sep}{mois:02}{sep}{'X'*lg}"
        self.lbl_preview_num.setText(preview)
    def save_numerotation(self):
        piece_map = {
            "Facture": "FAC",
            "Avoir": "AV",
            "Bon de livraison": "BL",
            "Devis": "DV",
            "Commande":"CMD"
        }

        type_piece = piece_map[self.cmb_piece_num.currentText()]

        conn = self.cal.connect_to_db(self.db_path)
        if conn is None:
            return 
        cur = conn.cursor()

        cur.execute("""
            INSERT OR REPLACE INTO numerotation (
                type_piece, prefixe, separateur,
                longueur, reset_mode
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            type_piece,
            self.ed_prefixe.text().strip(),
            self.cmb_sep.currentText(),
            self.spin_longueur.value(),
            self.cmb_reset.currentText()
        ))

        conn.commit()

        QMessageBox.information(
            self, "Numérotation",
            "Paramétrage de numérotation enregistré avec succès"
        )
    def charger_numerotation(self):
        piece_map = {
            "Facture": "FAC",
            "Avoir": "AV",
            "Bon de livraison": "BL",
            "Devis": "DV",
            "Commande":"CMD",
        }

        code = piece_map[self.cmb_piece_num.currentText()]

        conn = self.cal.connect_to_db(self.db_path)
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("""
            SELECT prefixe, separateur, longueur, reset_mode
            FROM numerotation WHERE type_piece=?
        """, (code,))
        row = cur.fetchone()

        if row:
            self.ed_prefixe.setText(row[0])
            self.cmb_sep.setCurrentText(row[1])
            self.spin_longueur.setValue(row[2])
            self.cmb_reset.setCurrentText(row[3])

        self.update_preview_num()

    # onglet pour afficher tous les informations
    def _ini_onglet_affiche(self):
        self.curentTab = self.tabs.currentIndex()
        conn = self.cal.connect_to_db(self.db_path)
        if conn is None:
            return
        cur = conn.cursor()
        if self.curentTab == 0:
            sqls = '''SELECT * from infoentre'''
            cur.execute(sqls)
            resu = cur.fetchone()
            if resu:
                nom_entreprise = resu[0]  
                tele = resu[1]
                tele1 = resu[2]
                detail = resu[3]
                nom1 = resu[4]
                adr = resu[5]
                ville = resu[6]
                ifu = resu[7]
                autre = resu[8]
           
                self.nom_entreprise.setText(nom_entreprise)
                self.tel1.setText(tele)
                self.tel2.setText(tele1)
                self.autre.setText(autre)
                self.responsable.setText(nom1)
                self.adresse.setText(adr)
                self.ville.setText(ville)
                self.ifu.setText(ifu)
                self.details.setText(detail)
                conn.close()
        if self.curentTab == 1:
            sqls = '''SELECT date_debut,date_fin,devise,tva from config'''
            cur.execute(sqls)
            resu = cur.fetchone()
            if resu:
                date_debu = resu[0]  
                date_fin = resu[1]
                date_debu = QDate.fromString(resu[0], "yyyy-MM-dd")
                date_fin = QDate.fromString(resu[1], "yyyy-MM-dd")
                devise=resu[2]
                tva=resu[3]
                self.date_debut.setDate(date_debu)
                self.date_fin.setDate(date_fin)
                self.devise.setText(str(devise))
                self.tva.setValue(float(tva))
            conn.close()
        elif self.curentTab == 2:
            sqls = '''SELECT nom,paswrd,email,id_int from login'''
            cur.execute(sqls)
            resu = cur.fetchall()
            if resu:
                for row_data in resu:
                    row = self.table_users.rowCount()
                    self.table_users.insertRow(row)
                    self.table_users.setItem(row, 0, QTableWidgetItem(str(row_data[0])))
                    self.table_users.setItem(row, 1, QTableWidgetItem(str(row_data[1])))
                    self.table_users.setItem(row, 2, QTableWidgetItem(str(row_data[2])))
                    self.table_users.setItem(row, 3, QTableWidgetItem(str(row_data[3])))
            conn.close()
        
        
    # === Onglet Utilisateurs ===
    def _init_onglet_users(self):

        layout = QVBoxLayout(self.tab_users)

        # Sous-onglets internes
        self.user_tabs = QTabWidget()
        layout.addWidget(self.user_tabs)

        # ===== Onglet 1 : Gestion Utilisateurs =====
        self.tab_user_list = QWidget()
        self.user_tabs.addTab(self.tab_user_list, "Utilisateurs")

        user_layout = QVBoxLayout(self.tab_user_list)
        box_h = QHBoxLayout() 
        self.user_name = QLineEdit()
        self.user_pass = QLineEdit()           
        self.user_email = QLineEdit() 
        self.user_email.setPlaceholderText("Email utilisateur")
        self.user_name.setPlaceholderText("Nom utilisateur")
        self.user_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.role = QComboBox()
        self.role.addItems(self.get_roles())
        form = QFormLayout()
        form.addRow("Nom utilisateur:", self.user_name)
        form.addRow("Mot de passe:", self.user_pass)
        form.addRow("Email utilisateur:", self.user_email)
        form.addRow("Rôle:",self.role)
        self.btn_add_user = QPushButton("Ajouter utilisateur")
        self.btn_add_user.clicked.connect(self.add_user)
        box_h.addWidget(self.btn_add_user)
        self.table_users = QTableWidget(0, 3)
        self.table_users.setHorizontalHeaderLabels(["Utilisateur", "Mot de passe", "Email"])
        user_layout.addLayout(form)
        user_layout.addWidget(self.btn_add_user)
        user_layout.addWidget(self.table_users)
        
        # ===== Onglet 2 : Gestion des Rôles =====
        self.tab_roles = RoleManager(self.db_path)
        self.user_tabs.addTab(self.tab_roles, "Rôles")

        # ===== Onglet 3 : Permissions =====
        self.tab_permissions = PermissionEditor(self.db_path)
        self.user_tabs.addTab(self.tab_permissions, "Permissions")

    def get_roles(self):
        conn = self.cal.connect_to_db(self.db_path)
        if conn is None:
            return []
        cur = conn.cursor()
        cur.execute("SELECT name FROM roles")
        roles = [row[0] for row in cur.fetchall()]
        conn.close()
        return roles
    def add_user(self):

        name = self.user_name.text().strip()
        pwd = self.user_pass.text().strip()
        email = self.user_email.text().strip()
        role_name = self.role.currentText()

        if not name or not pwd:
            QMessageBox.warning(self, "Erreur", "Nom ou mot de passe vide")
            return

        if not self.verifie_mot(pwd):
            QMessageBox.warning(self, "Sécurité",
                                "Mot de passe faible.\nMinimum 4 caractères + majuscule + minuscule + chiffre + symbole.")
            return

        conn = self.cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        # récupérer role_id
        cur.execute("SELECT id FROM roles WHERE name=?", (role_name,))
        role = cur.fetchone()

        if not role:
            QMessageBox.warning(self, "Erreur", "Rôle introuvable")
            return

        role_id = role[0]
        recovery_code = self.generate_recovery_code()
        mot_hash = hash_password(pwd)

        cur.execute("""
            INSERT INTO users (username, password, email, role_id, recovery_code)
            VALUES (?, ?, ?, ?, ?)
        """, (name, mot_hash, email, role_id, recovery_code))

        conn.commit()
        conn.close()

        QMessageBox.information(
            self,
            "Utilisateur créé",
            f"Utilisateur {name} créé.\nCode de secours : {recovery_code}"
        )

        self.user_name.clear()
        self.user_pass.clear()
        self.user_email.clear()

        self.load_users()

        
    def verifie_mot(self,mot):
        if len(mot) < 4:
            return False
        symb = re.compile(r'[\W_]')
        chif = re.compile(r'\d')
        Maj = re.compile(r'[A-z]')
        minis = re.compile(r'[a-z]')
        if (symb.search(mot) and chif.search(mot) and Maj.search(mot) and minis.search(mot)):
            return True
        else:
            return False
    
    import secrets

    def generate_recovery_code(self):
        return secrets.token_hex(8)  # Exemple : 'a3f9c2d1b4e5f678'

    # === Sauvegarde en BD ===
    def save_all(self):
        try:
            self.curentTab = self.tabs.currentIndex()
            conn = self.cal.connect_to_db(self.db_path)
            if conn is None:
                return
            cur = conn.cursor()

            # 1) Enregistrer entreprise
            if self.curentTab == 0:
                cur.execute("SELECT COUNT(*) FROM infoentre")
                result = cur.fetchone()[0]
                if result > 0:
                    QMessageBox.warning(self,"Restriction","Les informations de l'entreprise sont déjà enregistrée." "Vous ne pouvez pas en ajouter une nouvelle.")
                    conn.close()
                    return
                cur.execute("""
                    INSERT INTO infoentre (nom, tele, tele1, detail, nom1, adr, ville, ifu, autre)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.cal.nom_upper(self.nom_entreprise.text()), self.tel1.text(), self.tel2.text(),
                    self.autre.text(),self.cal.nom_upper(self.responsable.text()) ,
                    self.adresse.text(), self.ville.text(),
                    self.ifu.text(), self.autre.text()
                ))

            # 2) Enregistrer exercice + logo
            elif self.curentTab == 1:
                cur.execute("SELECT COUNT(*) FROM config")
                result = cur.fetchone()[0]
                cur.execute("""
                    INSERT INTO config (date_debut, date_fin, devise, tva)
                    VALUES (?, ?, ?, ?)
                """, (
                    self.date_debut.date().toString("yyyy-MM-dd"),
                    self.date_fin.date().toString("yyyy-MM-dd"),
                    self.devise.text(), self.tva.value()
                ))
                   
            # 3) Enregistrer utilisateurs
            else:
                for i in range(self.table_users.rowCount()):
                    user = self.table_users.item(i, 0)
                    if user is None:
                        return
                    user_txt = user.text()
                    pwd = self.table_users.item(i, 1)
                    if pwd is None:
                        return
                    pwd_txt = pwd.text()
                    mot_ = hash_password(pwd_txt)
                    
                    email = self.table_users.item(i, 2)
                    if email is None:
                        return
                    email_txt = email.text()

                    
                    recovery_code = self.generate_recovery_code()
                    cur.execute("INSERT INTO login (nom, paswrd,email,recovery_code) VALUES (?,? , ?, ?)", (user_txt, mot_,email_txt, recovery_code))
                    # Sauvegarde sur Google Drive
                    # Sauvegarde du mot de passe dans Google Drive
                    QMessageBox.information(self, "Utilisateur ajouté",
                    f"Utilisateur {user_txt} créé.\nCode de secours : {recovery_code}\n⚠️ Conservez-le précieusement.")
    
                    
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Succès", "Configuration enregistrée ✅")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'enregistrer : {e}")
            self.close()    
   
    def affiche_config(self):
        """Charge la configuration depuis un fichier JSON."""
        
        try:
            conn = cal.connect_to_db(self.db_path)
            if conn is None:
                return
            cur = conn.cursor()
            sqls = '''SELECT date_debut,date_fin,devise,tva from config'''
            cur.execute(sqls)
            resu = cur.fetchone()
            if resu:
                date_debu = resu[0]  
                date_fin = resu[1]
                date_debu = QDate.fromString(resu[0], "yyyy-MM-dd")
                date_fin = QDate.fromString(resu[1], "yyyy-MM-dd")
                devise=resu[2]
                tva=resu[3]
                self.date_debut.setDate(date_debu)
                self.date_fin.setDate(date_fin)
                self.devise.setText(str(devise))
                self.tva.setValue(float(tva))
                
        except FileNotFoundError:
            pass

# === Boîte de dialogue de réinitialisation du mot de passe ===
class ResetPasswordDialog(QDialog):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.setWindowTitle("Réinitialisation du mot de passe")
        self.resize(300, 200)
        self.setWindowIcon(QIcon(":/icon/parametre-dutilisateur.png"))
        layout = QVBoxLayout(self)

        self.user = QLineEdit(); self.user.setPlaceholderText("Nom utilisateur ou email")
        self.code = QLineEdit(); self.code.setPlaceholderText("Code de secours")
        self.newpwd = QLineEdit(); self.newpwd.setPlaceholderText("Nouveau mot de passe"); self.newpwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm = QLineEdit(); self.confirm.setPlaceholderText("Confirmer mot de passe"); self.confirm.setEchoMode(QLineEdit.EchoMode.Password)

        btn = QPushButton("👽Réinitialiser")
        
        btn.clicked.connect(self.reset_password)

        for w in [self.user, self.code, self.newpwd, self.confirm, btn]:
            layout.addWidget(w)

    def reset_password(self):
        if self.newpwd.text() != self.confirm.text():
            QMessageBox.warning(self, "Erreur", "Les mots de passe ne correspondent pas")
            return

        conn = cal.connect_to_db(self.db_path)
        if conn is None:
            QMessageBox.warning(self, "Erreur", "Connexion base impossible")
            return
        cur = conn.cursor()
        cur.execute("SELECT uid, recovery_code FROM login WHERE nom=? OR email=?", (self.user.text(), self.user.text()))
        row = cur.fetchone()
        if not row:
            QMessageBox.warning(self, "Erreur", "😥Utilisateur introuvable")
            return
        if row[1] != self.code.text():
            QMessageBox.warning(self, "Erreur", "😥Code de secours invalide")
            return

        mot_hache = hash_password(self.newpwd.text())
        cur.execute("UPDATE login SET paswrd=? WHERE uid=?", (mot_hache, row[0]))
        conn.commit()
        conn.close()
        QMessageBox.information(self, "Succès", "Mot de passe réinitialisé ✅")
        self.accept()
