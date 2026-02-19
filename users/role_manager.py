from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget,
    QPushButton, QHBoxLayout,
    QInputDialog, QMessageBox
)
from fonction.methode import cal


class RoleManager(QWidget):

    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.init_ui()
        self.load_roles()

    def init_ui(self):

        layout = QVBoxLayout(self)

        self.list_roles = QListWidget()
        layout.addWidget(self.list_roles)

        btn_layout = QHBoxLayout()

        self.btn_add = QPushButton("Ajouter")
        self.btn_edit = QPushButton("Renommer")
        self.btn_delete = QPushButton("Supprimer")

        self.btn_add.clicked.connect(self.add_role)
        self.btn_edit.clicked.connect(self.rename_role)
        self.btn_delete.clicked.connect(self.delete_role)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)

        layout.addLayout(btn_layout)

    def load_roles(self):

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT id, name FROM roles")
        roles = cur.fetchall()
        conn.close()

        self.list_roles.clear()

        for role in roles:
            self.list_roles.addItem(f"{role[0]} - {role[1]}")

    def add_role(self):

        name, ok = QInputDialog.getText(self, "Nouveau rôle", "Nom du rôle :")

        if ok and name:

            conn = cal.connect_to_db(self.db_path)
            cur = conn.cursor()

            cur.execute("INSERT INTO roles (name) VALUES (?)", (name,))
            conn.commit()
            conn.close()

            self.load_roles()

    def rename_role(self):

        item = self.list_roles.currentItem()
        if not item:
            return

        role_id = int(item.text().split(" - ")[0])

        new_name, ok = QInputDialog.getText(self, "Renommer", "Nouveau nom :")

        if ok and new_name:

            conn = cal.connect_to_db(self.db_path)
            cur = conn.cursor()

            cur.execute("UPDATE roles SET name=? WHERE id=?", (new_name, role_id))
            conn.commit()
            conn.close()

            self.load_roles()

    def delete_role(self):

        item = self.list_roles.currentItem()
        if not item:
            return

        role_id = int(item.text().split(" - ")[0])
        role_name = item.text().split(" - ")[1]

        if role_name.upper() == "ADMIN":
            QMessageBox.warning(self, "Erreur",
                                "Impossible de supprimer le rôle ADMIN.")
            return

        confirm = QMessageBox.question(
            self, "Confirmation",
            f"Supprimer le rôle {role_name} ?"
        )

        if confirm != QMessageBox.Yes:
            return

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        cur.execute("DELETE FROM roles WHERE id=?", (role_id,))
        cur.execute("DELETE FROM permissions WHERE role_id=?", (role_id,))

        conn.commit()
        conn.close()

        self.load_roles()
