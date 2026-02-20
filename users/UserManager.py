from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt
from fonction.methode import cal
from fonction.model import hash_password
import random
import string
from core.services.email_service import EmailService


class UserManager(QWidget):

    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.init_ui()
        self.load_roles()
        self.load_users()
        

    # ================= UI =================

    def init_ui(self):

        layout = QVBoxLayout(self)

        # ==== FORMULAIRE ====
        form_layout = QHBoxLayout()

        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Nom utilisateur")

        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Mot de passe")
        self.input_password.setEchoMode(QLineEdit.Password)

        self.input_email = QLineEdit()
        self.input_email.setPlaceholderText("Email")

        self.combo_role = QComboBox()

        self.check_actif = QCheckBox("Actif")
        self.check_actif.setChecked(True)

        self.btn_add = QPushButton("Créer")
        self.btn_add.clicked.connect(self.add_user)
        self.input_password.setEchoMode(QLineEdit.Password)

        self.btn_toggle_pass = QPushButton("👁")
        self.btn_toggle_pass.setFixedWidth(40)
        self.btn_toggle_pass.clicked.connect(self.toggle_password)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher utilisateur...")
        self.search_input.textChanged.connect(self.search_user)

        layout.insertWidget(0, self.search_input)

        form_layout.addWidget(self.btn_toggle_pass)
        form_layout.addWidget(self.input_username)
        form_layout.addWidget(self.input_password)
        form_layout.addWidget(self.input_email)
        form_layout.addWidget(self.combo_role)
        form_layout.addWidget(self.check_actif)
        form_layout.addWidget(self.btn_add)

        layout.addLayout(form_layout)

        # ==== TABLE UTILISATEURS ====
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Username", "Email", "Rôle", "Actif", "Actions"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnHidden(0, True)
        self.table.cellDoubleClicked.connect(self.edit_user)

        layout.addWidget(self.table)

    # Recherche utilisateur
    def search_user(self, text):

        for row in range(self.table.rowCount()):

            username = self.table.item(row, 1).text().lower()

            if text.lower() in username:
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)
    # ================= LOAD DATA =================

    def load_roles(self):

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT id, name FROM roles")
        roles = cur.fetchall()
        conn.close()

        self.combo_role.clear()

        for role in roles:
            self.combo_role.addItem(role[1], role[0])
    
    def edit_user(self, row, column):

        user_id = int(self.table.item(row, 0).text())

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT username, email, role_id, actif
            FROM users
            WHERE id=?
        """, (user_id,))

        user = cur.fetchone()
        conn.close()

        if not user:
            return

        self.input_username.setText(user[0])
        self.input_email.setText(user[1] or "")
        self.combo_role.setCurrentIndex(
            self.combo_role.findData(user[2])
        )
        self.check_actif.setChecked(bool(user[3]))

        self.current_edit_id = user_id
    def load_users(self):

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT u.id, u.username, u.email,
            r.name, u.actif, u.is_connected
            FROM users u
            JOIN roles r ON r.id = u.role_id
        """)

        users = cur.fetchall()
        conn.close()

        self.table.setRowCount(len(users))

        for row, user in enumerate(users):

            self.table.setItem(row, 0, QTableWidgetItem(str(user[0])))
            self.table.setItem(row, 1, QTableWidgetItem(user[1]))
            self.table.setItem(row, 2, QTableWidgetItem(user[2] or ""))
            self.table.setItem(row, 3, QTableWidgetItem(user[3]))
            self.table.setItem(row, 4,
                QTableWidgetItem("🟢 En ligne" if user[5] else "⚪ Hors ligne")
            )
            # Boutons actions
            btn_delete = QPushButton("Supprimer")
            btn_delete.clicked.connect(
                lambda _, uid=user[0]: self.delete_user(uid)
            )

            self.table.setCellWidget(row, 5, btn_delete)
            # Bouton reset password
            btn_reset = QPushButton("Reset MDP")
            btn_reset.clicked.connect(
                lambda _, uid=user[0]: self.reset_password(uid)
            )
            self.table.setCellWidget(row, 5, btn_reset)
            

    # def reset_password(self, user_id):

    #     new_pass = "1234"

    #     conn = cal.connect_to_db(self.db_path)
    #     cur = conn.cursor()

    #     cur.execute("""
    #         UPDATE users
    #         SET password=?
    #         WHERE id=?
    #     """, (hash_password(new_pass), user_id))

    #     conn.commit()
    #     conn.close()

    #     QMessageBox.information(self, "Succès",
                                # "Mot de passe réinitialisé à 1234")
 

    def reset_password(self, user_id):

        new_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT email FROM users WHERE id=?", (user_id,))
        email = cur.fetchone()[0]

        cur.execute("""
            UPDATE users
            SET password=?, failed_attempts=0
            WHERE id=?
        """, (hash_password(new_pass), user_id))

        conn.commit()
        conn.close()

        if email:
            EmailService().send_reset(email, new_pass)

        QMessageBox.information(self, "Succès",
                                "Mot de passe envoyé par email.")
    # ================= CRUD =================

    # Ajout / Modification d'un utilisateur
    def add_user(self):

        username = self.input_username.text().strip()
        password = self.input_password.text().strip()
        email = self.input_email.text().strip()
        role_id = self.combo_role.currentData()
        actif = 1 if self.check_actif.isChecked() else 0

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        if hasattr(self, "current_edit_id"):

            cur.execute("""
                UPDATE users
                SET username=?, email=?, role_id=?, actif=?
                WHERE id=?
            """, (username, email, role_id, actif, self.current_edit_id))

            if password:
                cur.execute("""
                    UPDATE users
                    SET password=?
                    WHERE id=?
                """, (hash_password(password), self.current_edit_id))

            del self.current_edit_id

        else:

            cur.execute("""
                INSERT INTO users (username, password, email, role_id, actif)
                VALUES (?, ?, ?, ?, ?)
            """, (username, hash_password(password), email, role_id, actif))

        conn.commit()
        conn.close()

        self.clear_form()
        self.load_users()

    # Suppression d'un utilisateur
    def delete_user(self, user_id):

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        # Vérifier si dernier ADMIN
        cur.execute("""
            SELECT r.name
            FROM users u
            JOIN roles r ON r.id = u.role_id
            WHERE u.id=?
        """, (user_id,))

        role = cur.fetchone()

        if role and role[0].upper() == "ADMIN":

            cur.execute("""
                SELECT COUNT(*)
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE r.name='ADMIN'
            """)
            count_admin = cur.fetchone()[0]

            if count_admin <= 1:
                QMessageBox.warning(self, "Erreur",
                                    "Impossible de supprimer le dernier ADMIN.")
                conn.close()
                return

        confirm = QMessageBox.question(
            self, "Confirmation",
            "Supprimer cet utilisateur ?"
        )

        if confirm != QMessageBox.Yes:
            conn.close()
            return

        cur.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        conn.close()

        self.load_users()
    
    # Toggle visibilité du mot de passe
    def toggle_password(self):
        if self.input_password.echoMode() == QLineEdit.Password:
            self.input_password.setEchoMode(QLineEdit.Normal)
        else:
            self.input_password.setEchoMode(QLineEdit.Password)
    
    def clear_form(self):
        self.input_username.clear()
        self.input_password.clear()
        self.input_email.clear()
        self.check_actif.setChecked(True)