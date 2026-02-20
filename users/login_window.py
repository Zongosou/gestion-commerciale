import ctypes

from PySide6.QtWidgets import (
    QApplication, QDialog, QProgressBar, QVBoxLayout, QLabel,
    QLineEdit, QPushButton,
    QMessageBox, QHBoxLayout,
    QCheckBox
)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QRegion
from PySide6.QtCore import QTimer, Qt, QSettings

from core.services.auth_service import AuthService


class LoginWindow(QDialog):

    def __init__(self, db_path, logo_path=None):
        super().__init__()

        self.db_path = db_path
        self.logo_path = logo_path
        self.auth = AuthService(db_path)
        self.user_id = None
        self.user = None

        self.settings = QSettings("MonERP", "Connexion")

        self.setWindowTitle("Connexion GesCom")
        screen = QApplication.primaryScreen()
        size = screen.availableGeometry()
        w = int(size.width() * 0.4)
        h = int(size.height() * 0.4)
        self.resize(w, h)
        self.setWindowIcon(QIcon(":/icon/icone.png"))

        self.init_ui()
        self.load_saved_user()

    # ================= UI =================

    def init_ui(self):

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        # ===== Logo rond avec ombre =====
        if self.logo_path:
            logo_label = QLabel()
            pixmap = QPixmap(self.logo_path).scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            # rond
            mask = QRegion(0, 0, 120, 120, QRegion.Ellipse)
            logo_label.setMask(mask)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("""
                QLabel {
                    border-radius: 60px;
                    background-color: white;
                }
            """)
            layout.addWidget(logo_label)

        # ===== Username =====
        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("Nom utilisateur")
        layout.addWidget(self.input_user)

        # ===== Password =====
        pass_layout = QHBoxLayout()

        self.input_pass = QLineEdit()
        self.input_pass.setPlaceholderText("Mot de passe")
        self.input_pass.setEchoMode(QLineEdit.Password)
        self.input_pass.textChanged.connect(self.detect_capslock)

        self.btn_toggle = QPushButton("👁")
        self.btn_toggle.setFixedWidth(40)
        self.btn_toggle.clicked.connect(self.toggle_password)

        pass_layout.addWidget(self.input_pass)
        pass_layout.addWidget(self.btn_toggle)

        layout.addLayout(pass_layout)

        # ===== Alerte CapsLock =====
        self.label_caps = QLabel("")
        self.label_caps.setStyleSheet("color: red; font-size: 11px;")
        layout.addWidget(self.label_caps)

        # ===== Se souvenir =====
        self.checkbox_remember = QCheckBox("Se souvenir de moi")
        layout.addWidget(self.checkbox_remember)

        # ===== Bouton connexion =====
        self.btn_login = QPushButton("Connexion")
        self.btn_login.clicked.connect(self.handle_login)
        layout.addWidget(self.btn_login)
        

        # ===== Mot de passe oublié =====
        self.btn_forgot = QPushButton("Mot de passe oublié ?")
        self.btn_forgot.setFlat(True)
        self.btn_forgot.clicked.connect(self.forgot_password)
        layout.addWidget(self.btn_forgot)

        # ===== Loader =====
        self.loader = QProgressBar()
        self.loader.setRange(0, 0)  # mode indéterminé
        self.loader.setVisible(False)
        layout.addWidget(self.loader)

        # ===== Style moderne =====
        self.setStyleSheet("""
            QDialog {
                background-color: #f4f6f9;
            }
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                border-radius: 6px;
                border: 1px solid #ccc;
            }
            QPushButton {
                padding: 8px;
                font-weight: bold;
                border-radius: 6px;
                background-color: #0078D7;
                color: white;
            }
            QPushButton:hover {
                background-color: #005fa3;
            }
        """)

    # ================= Password toggle =================

    def toggle_password(self):

        if self.input_pass.echoMode() == QLineEdit.Password:
            self.input_pass.setEchoMode(QLineEdit.Normal)
        else:
            self.input_pass.setEchoMode(QLineEdit.Password)

    # ================= CapsLock detection =================

    def detect_capslock(self):

        if ctypes.windll.user32.GetKeyState(0x14) & 1:
            self.label_caps.setText("⚠ Caps Lock activé")
        else:
            self.label_caps.setText("")

    # ================= Login =================

    def handle_login(self):

        username = self.input_user.text().strip()
        password = self.input_pass.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Erreur",
                                "Veuillez remplir tous les champs.")
            return

        # 🔒 Désactiver bouton
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Connexion en cours...")
        self.loader.setVisible(True)

        # Laisser le loader s'afficher avant traitement
        QTimer.singleShot(100, lambda: self.process_login(username, password))

    # ================= Forgot password =================

    def forgot_password(self):

        username = self.input_user.text().strip()

        if not username:
            QMessageBox.warning(self, "Info",
                                "Entrez votre nom utilisateur d'abord.")
            return

        QMessageBox.information(
            self,
            "Réinitialisation",
            "Un email de réinitialisation a été envoyé (simulation)."
        )

        # appeler ton service email reset

    # ================= Remember me =================

    def load_saved_user(self):

        saved = self.settings.value("username")
        if saved:
            self.input_user.setText(saved)
            self.checkbox_remember.setChecked(True)

    #================= Process login =================
    def process_login(self, username, password):

        auth_result = self.auth.login(username, password)

        if isinstance(auth_result, tuple):
            if len(auth_result) == 3:
                success, result, login_user = auth_result
            elif len(auth_result) == 2:
                success, result = auth_result
                login_user = username
            else:
                success, result = False, "Reponse d'authentification invalide"
                login_user = None
        else:
            success, result = False, "Reponse d'authentification invalide"
            login_user = None

        # Réactiver bouton
        self.loader.setVisible(False)
        self.btn_login.setEnabled(True)
        self.btn_login.setText("Connexion")

        if success:
            self.user_id = result
            self.user = login_user
            self.accept()
        else:
            QMessageBox.warning(self, "Connexion échouée", result)
