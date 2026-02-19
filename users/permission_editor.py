from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QTableWidget, QTableWidgetItem,
    QCheckBox, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt
from fonction.methode import cal


MODULES = [
    "DEVIS",
    "COMMANDE",
    "BON_LIVRAISON",
    "FACTURE",
    "STOCK",
    "UTILISATEURS"
]

ACTIONS = [
    "create",
    "edit",
    "delete",
    "validate",
    "print",
    "view"
]


class PermissionEditor(QWidget):

    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.init_ui()
        self.load_roles()

    def init_ui(self):

        layout = QVBoxLayout(self)

        # Sélection rôle
        role_layout = QHBoxLayout()
        role_layout.addWidget(QLabel("Rôle :"))

        self.role_combo = QComboBox()
        self.role_combo.currentIndexChanged.connect(self.load_permissions)
        role_layout.addWidget(self.role_combo)

        layout.addLayout(role_layout)

        # Tableau
        self.table = QTableWidget()
        self.table.setColumnCount(len(ACTIONS) + 1)
        self.table.setHorizontalHeaderLabels(["Module"] + ACTIONS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #ddd;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 4px;
                border: none;
            }
        """)

        layout.addWidget(self.table)

        # Boutons
        btn_layout = QHBoxLayout()

        self.btn_all = QPushButton("Tout cocher")
        self.btn_none = QPushButton("Tout décocher")
        self.btn_copy = QPushButton("Copier d’un rôle")
        self.btn_save = QPushButton("Enregistrer")

        self.btn_all.clicked.connect(self.check_all)
        self.btn_none.clicked.connect(self.uncheck_all)
        self.btn_copy.clicked.connect(self.copy_permissions)
        self.btn_save.clicked.connect(self.save_permissions)

        btn_layout.addWidget(self.btn_all)
        btn_layout.addWidget(self.btn_none)
        btn_layout.addWidget(self.btn_copy)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)

    def load_roles(self):

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        cur.execute("SELECT id, name FROM roles")
        roles = cur.fetchall()

        conn.close()

        self.role_combo.clear()

        for role in roles:
            self.role_combo.addItem(role[1], role[0])

    def load_permissions(self):

        role_id = self.role_combo.currentData()
        if not role_id:
            return

        self.table.setRowCount(len(MODULES))

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        for row, module in enumerate(MODULES):

            self.table.setItem(row, 0, QTableWidgetItem(module))

            for col, action in enumerate(ACTIONS, start=1):

                cur.execute("""
                    SELECT allowed
                    FROM permissions
                    WHERE role_id=? AND module=? AND action=?
                """, (role_id, module, action))

                result = cur.fetchone()
                allowed = result[0] if result else 0

                checkbox = QCheckBox()
                checkbox.setChecked(allowed == 1)
                wrapper = QWidget()
                wrapper_layout = QHBoxLayout(wrapper)
                wrapper_layout.setContentsMargins(0, 0, 0, 0)
                wrapper_layout.setAlignment(Qt.AlignCenter)
                wrapper_layout.addWidget(checkbox)

                self.table.setCellWidget(row, col, wrapper)

        conn.close()

    def _get_checkbox(self, row, col):
        widget = self.table.cellWidget(row, col)
        if widget is None:
            return None
        if isinstance(widget, QCheckBox):
            return widget
        return widget.findChild(QCheckBox)

    def check_all(self):
        for row in range(self.table.rowCount()):
            for col in range(1, self.table.columnCount()):
                checkbox = self._get_checkbox(row, col)
                if checkbox is not None:
                    checkbox.setChecked(True)

    def uncheck_all(self):
        for row in range(self.table.rowCount()):
            for col in range(1, self.table.columnCount()):
                checkbox = self._get_checkbox(row, col)
                if checkbox is not None:
                    checkbox.setChecked(False)

    def copy_permissions(self):

        role_id = self.role_combo.currentData()
        if not role_id:
            return

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT module, action, allowed
            FROM permissions
            WHERE role_id=?
        """, (role_id,))

        permissions = cur.fetchall()
        conn.close()

        for module, action, allowed in permissions:

            if module in MODULES and action in ACTIONS:
                row = MODULES.index(module)
                col = ACTIONS.index(action) + 1
                checkbox = self._get_checkbox(row, col)
                if checkbox is not None:
                    checkbox.setChecked(allowed == 1)

    def save_permissions(self):

        role_id = self.role_combo.currentData()
        if not role_id:
            return

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        for row, module in enumerate(MODULES):

            for col, action in enumerate(ACTIONS, start=1):

                checkbox = self._get_checkbox(row, col)
                allowed = 1 if checkbox and checkbox.isChecked() else 0

                cur.execute("""
                    UPDATE permissions
                    SET allowed=?
                    WHERE role_id=? AND module=? AND action=?
                """, (allowed, role_id, module, action))

                if cur.rowcount == 0:
                    cur.execute("""
                        INSERT INTO permissions (role_id, module, action, allowed)
                        VALUES (?, ?, ?, ?)
                    """, (role_id, module, action, allowed))

        conn.commit()
        conn.close()

        QMessageBox.information(self, "Succès",
                                "Permissions enregistrées avec succès.")
