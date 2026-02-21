
import sys
import ctypes
import platform
import os
import keyring
from PySide6.QtWidgets import (
    QApplication, QDialog, QProgressBar, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QHBoxLayout,
    QCheckBox, QWidget
)
from PySide6.QtGui import (
    QCursor, QIcon, QPixmap, QPainter, QPainterPath, 
    QAction, QColor, QPen
)
from PySide6.QtCore import (
    QTimer, Qt, QSize, QRunnable, 
    QThreadPool, Signal, QObject, Slot
)
# --- Style Constants ---
STYLE_CONSTANTS = {
    "background_color": "#2C2B2B",
    "input_field_color": "#374151",
    "input_border_color": "#4B5563",
    "input_error_color": "#EF4444",  # Red for errors
    "success_color": "#10B981",      # Green for success
    "primary_button_color": "#6366F1",
    "primary_button_hover_color": "#4F46E5",
    "secondary_button_color": "#374151",
    "secondary_button_hover_color": "#4B5563",
    "text_color": "#E5E7EB",
    "text_secondary_color": "#9CA3AF",
    "link_color": "#6366F1",
    "separator_color": "#6B7280",
    "font_family": "Inter, sans-serif",
}
# Simulation du service (à importer de votre core.services)
from core.services.auth_service import AuthService
# --- Custom Widgets ---

# =========================================================
# BOUTON AVEC ICÔNE SVG RECOLORABLE (HOVER INCLUS)
class HoverIconButton(QPushButton):
    """
    A custom button that recolors its SVG icon on hover.
    Includes caching for performance.
    """
    def __init__(self, icon_path, parent=None):
        super().__init__(parent)
        self.icon_path = icon_path
        self.default_color = STYLE_CONSTANTS["text_secondary_color"]
        self.hover_color = "#FFFFFF"
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("border: none; background: transparent;")
        self.setFixedSize(24, 24)
        
        # Cache pixmaps to prevent lag
        self._default_pixmap = self._create_pixmap(self.default_color)
        self._hover_pixmap = self._create_pixmap(self.hover_color)
        
        # Set initial state
        self.setIcon(QIcon(self._default_pixmap))

    def _create_pixmap(self, color_hex):
        if not os.path.exists(self.icon_path):
            return QPixmap()
        try:
            with open(self.icon_path, 'r') as f:
                svg_data = f.read()
            colored_svg = svg_data.replace('currentColor', color_hex)
            pixmap = QPixmap()
            pixmap.loadFromData(colored_svg.encode('utf-8'))
            return pixmap
        except Exception as e:
            print(f"Error loading icon: {e}")
            return QPixmap()

    def enterEvent(self, event):
        if self._hover_pixmap:
            self.setIcon(QIcon(self._hover_pixmap))
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._default_pixmap:
            self.setIcon(QIcon(self._default_pixmap))
        super().leaveEvent(event)
    
    def set_icon_path(self, new_path):
        self.icon_path = new_path
        self._default_pixmap = self._create_pixmap(self.default_color)
        self._hover_pixmap = self._create_pixmap(self.hover_color)
        if self.underMouse():
            self.setIcon(QIcon(self._hover_pixmap))
        else:
            self.setIcon(QIcon(self._default_pixmap))
# =========================================================
# GESTION ASYNCHRONE (Worker & Signals)
# =========================================================

class AuthSignals(QObject):
    """Signaux pour communiquer entre le thread de calcul et l'UI."""
    finished = Signal(tuple)  # (success, result, user)
    error = Signal(str)

class AuthWorker(QRunnable):
    """Exécute la logique de connexion en arrière-plan."""
    def __init__(self, auth_service, username, password):
        super().__init__()
        self.auth_service = auth_service
        self.username = username
        self.password = password
        self.signals = AuthSignals()

    @Slot()
    def run(self):
        try:
            # Appel au service existant (simulé ici)
            auth_result = self.auth_service.login(self.username, self.password)
            self.signals.finished.emit(auth_result)
        except Exception as e:
            self.signals.error.emit(str(e))

# =========================================================
# COMPOSANTS UI PERSONNALISÉS
# =========================================================

class CircularLogo(QWidget):
    """Widget de logo avec rendu haute fidélité (Antialiasing)."""
    def __init__(self, image_path, size=120):
        super().__init__()
        self.setFixedSize(size, size)
        self.pixmap = QPixmap()
        if image_path and os.path.exists(image_path):
            src = QPixmap(image_path)
            if not src.isNull():
                self.pixmap = src.scaled(
                    size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Création du chemin circulaire
        path = QPainterPath()
        path.addEllipse(0, 0, self.width(), self.height())
        
        painter.setClipPath(path)
        if not self.pixmap.isNull():
            painter.drawPixmap(0, 0, self.pixmap)
        else:
            painter.fillPath(path, QColor("#f2f2f2"))
        
        # Bordure légère pour la finition
        painter.setPen(QPen(QColor("#d1d1d1"), 1))
        painter.drawEllipse(0, 0, self.width()-1, self.height()-1)

class PasswordLineEdit(QLineEdit):
    """Champ de mot de passe avec bouton de visibilité intégré."""
    def __init__(self):
        super().__init__()
        self.setEchoMode(QLineEdit.Password)
        self.setPlaceholderText("Mot de passe")
        self.setFixedHeight(40)
        self.default_input_style = f"""
            QLineEdit {{
                background-color: {STYLE_CONSTANTS['input_field_color']};
                color: {STYLE_CONSTANTS['text_color']};
                font-size: 14px;
                padding-left: 15px;
                padding-right: 15px;
                border-radius: 8px;
                border: 1px solid {STYLE_CONSTANTS['input_border_color']};
            }}
            QLineEdit:focus {{
                border: 1px solid {STYLE_CONSTANTS['primary_button_color']};
            }}
        """
        
        # Ajout de l'action "œil" directement dans le champ
        self.toggle_action = QAction(QIcon("interface/Eye.svg"),"", self)
        self.addAction(self.toggle_action, QLineEdit.TrailingPosition)
        self.toggle_action.triggered.connect(self.toggle_visibility)
        self.visible_state = False
        self.setStyleSheet(self.default_input_style)

    def toggle_visibility(self):
        self.visible_state = not self.visible_state
        self.setEchoMode(QLineEdit.Normal if self.visible_state else QLineEdit.Password)
        self.toggle_action.setText("🔒" if self.visible_state else "👁")

# =========================================================
# FENÊTRE DE CONNEXION PRINCIPALE
# =========================================================

class LoginWindow(QDialog):
    def __init__(self, db_path, logo_path=None):
        super().__init__()
        self.db_path = db_path
        self.logo_path = logo_path
        self.auth = AuthService(db_path)
        self.threadpool = QThreadPool()
        
        self.user_id = None
        self.user = None
        self.service_name = "MonERP_GesCom"

        self.init_window_props()
        self.init_ui()
        self.load_remembered_user()

    def init_window_props(self):
        self.setWindowTitle("Connexion GesCom")
        self.resize(500, 440)
        self.setMinimumSize(500, 400)
        self.setStyleSheet(f"background-color: {STYLE_CONSTANTS['background_color']};color:white;")
        self.center_window()
        self.setWindowIcon(QIcon(":/icon/icone.png"))
        

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Logo circulaire optimisé
        logo = QLabel(self)
        if self.logo_path and os.path.exists(self.logo_path):
            logo_container = QHBoxLayout()
            self.logo_widget = CircularLogo(self.logo_path)
            logo_container.addWidget(self.logo_widget, 0, Qt.AlignCenter)
            layout.addLayout(logo_container)
        else:
            logo_container = QHBoxLayout()
            self.logo_widget = CircularLogo(":/icon/icone.png", size=120)
            logo_container.addWidget(self.logo_widget, 0, Qt.AlignCenter)
            layout.addLayout(logo_container)
        # Champs de saisie
        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("Nom d'utilisateur")
        self.input_user.setFixedHeight(40)
        self.default_input_style = f"""
            QLineEdit {{
                background-color: {STYLE_CONSTANTS['input_field_color']};
                color: {STYLE_CONSTANTS['text_color']};
                font-size: 14px;
                padding-left: 15px;
                padding-right: 15px;
                border-radius: 8px;
                border: 1px solid {STYLE_CONSTANTS['input_border_color']};
            }}
            QLineEdit:focus {{
                border: 1px solid {STYLE_CONSTANTS['primary_button_color']};
            }}
        """
        self.input_user.setStyleSheet(self.default_input_style)
        layout.addWidget(self.input_user)

        self.input_pass = PasswordLineEdit()
        self.input_pass.textChanged.connect(self.detect_capslock)
        layout.addWidget(self.input_pass)

        # Alertes et Options
        self.label_caps = QLabel("")
        self.label_caps.setFixedHeight(30)
        self.label_caps.setStyleSheet("color: #F56C6C; font-size: 11px;")
        layout.addWidget(self.label_caps)

        self.check_remember = QCheckBox("Se souvenir de moi")
        self.check_remember.setFixedHeight(30)
        layout.addWidget(self.check_remember)

        # Actions
        self.btn_login = QPushButton("Connexion")
        self.btn_login.setFixedHeight(30)
        self.btn_login.setStyleSheet(f"""
            QPushButton {{
                background-color: {STYLE_CONSTANTS['primary_button_color']};
                color: white;
                font-size: 14px;
                font-weight: 600;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {STYLE_CONSTANTS['primary_button_hover_color']};
            }}
        """)
        self.btn_login.setObjectName("primaryBtn")
        self.btn_login.clicked.connect(self.start_login_process)
        layout.addWidget(self.btn_login)

        self.loader = QProgressBar()
        self.loader.setRange(0, 0)
        self.loader.setVisible(False)
        self.loader.setFixedHeight(4)
        layout.addWidget(self.loader)

        self.forgot_password_link = QLabel(f'<a href="#" style="color:{STYLE_CONSTANTS["link_color"]}; text-decoration:none;">Mot de passe oublié?</a>')
        self.forgot_password_link.setFixedHeight(20)
        self.forgot_password_link.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.forgot_password_link.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # self.forgot_password_link.linkActivated.connect(self._switch_to_forgot_password)
        # self.btn_forgot = QPushButton("Mot de passe oublié?")
        # self.btn_forgot.setFixedHeight(40)
        # self.btn_forgot.setFlat(True)
        # self.btn_forgot.setStyleSheet("color: #909399; font-size: 12px;")
        layout.addWidget(self.forgot_password_link, 0, Qt.AlignCenter)

    # Logic
    def detect_capslock(self):
        """Détection native du Caps Lock (Optimisé pour Windows)."""
        is_on = False
        if platform.system() == "Windows":
            is_on = ctypes.windll.user32.GetKeyState(0x14) & 1
        # Ajoutez ici les détections X11 pour Linux si nécessaire
        
        self.label_caps.setText("⚠ Verrouillage majuscule activé" if is_on else "")

    def load_remembered_user(self):
        """Récupération sécurisée via le trousseau système."""
        try:
            # On récupère le dernier user_id stocké via QSettings par exemple, 
            # mais le mot de passe ou token resterait dans keyring.
            # Ici on simplifie en récupérant juste le nom.
            from PySide6.QtCore import QSettings
            settings = QSettings("MonERP", "Connexion")
            saved_user = settings.value("last_user")
            if saved_user:
                self.input_user.setText(saved_user)
                self.check_remember.setChecked(True)
        except: pass

    def start_login_process(self):
        """Initialise la tâche asynchrone."""
        user = self.input_user.text().strip()
        pwd = self.input_pass.text().strip()

        if not user or not pwd:
            QMessageBox.warning(self, "Erreur", "Champs incomplets.")
            return

        # UI State
        self.btn_login.setEnabled(False)
        self.btn_login.setText("Authentification...")
        self.loader.setVisible(True)

        # Création du worker
        worker = AuthWorker(self.auth, user, pwd)
        worker.signals.finished.connect(self.on_login_result)
        worker.signals.error.connect(self.on_login_error)
        self.threadpool.start(worker)

    def on_login_result(self, result):
        """Gère le retour du thread de connexion."""
        self.loader.setVisible(False)
        self.btn_login.setEnabled(True)
        self.btn_login.setText("Connexion")

        success, data, login_user = self.parse_auth_data(result)

        if success:
            if self.check_remember.isChecked():
                # Stockage sécurisé
                keyring.set_password(self.service_name, "last_user", login_user)
            self.user_id = data
            self.user = login_user
            self.accept()
        else:
            QMessageBox.critical(self, "Échec", f"Accès refusé : {data}")

    def on_login_error(self, message):
        self.loader.setVisible(False)
        self.btn_login.setEnabled(True)
        QMessageBox.critical(self, "Erreur Système", message)

    def parse_auth_data(self, result):
        """Normalise la réponse du service d'authentification."""
        if isinstance(result, tuple):
            if len(result) == 3: return result
            if len(result) == 2: return (result[0], result[1], self.input_user.text())
        return (False, "Format de réponse invalide", None)
    # Centrage de la fenêtre
    def center_window(self):
        screen = self.screen().availableGeometry()
        self.move(
            int((screen.width() - self.width()) / 2),
            int((screen.height() - self.height()) / 2)
        )
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Exemple d'usage
    win = LoginWindow("db.sqlite", "logo.png")
    if win.exec() == QDialog.Accepted:
        print(f"Connecté : {win.user} (ID: {win.user_id})")
    sys.exit(app.exec())
