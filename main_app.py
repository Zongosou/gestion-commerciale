import sys

from PySide6.QtWidgets import (
QApplication, QDialog, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QStyle, QStyleFactory,
    QListWidget, QListWidgetItem, QSizePolicy, QSpacerItem,
    QStackedWidget,QMenuBar,QMenu
)

from PySide6.QtGui import QIcon
from caisse.TresorerieDash import SuiviTresorerie
from fonction.methode import cal
from users.login_window import LoginWindow
from users.widzar import SetupWizardTabs
from piece.piece_liste_patched import ListePiece
from stock.gest_stock import StockApp
from fonction.tiers import TiersWidget
from caisse.dashbord import Dashboard as RapportWindow
from  caisse.TresorerieDash import RapportManager
from interface.icon_rc import *
from core.services.auth_service import logout
import os
# ---------------------------
# fonction principale 
# ---------------------------
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data/stock.db'))
db_logo = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
class StockWindow(QMainWindow):
    def __init__(self,user=None):
        super().__init__()
        self.setWindowTitle(f"GsCom - Gestion Commerciale - {user}")
        self.setWindowIcon(QIcon(":/icon/icone.png"))
        # Taille adaptée : par exemple 80% de l'écran
        screen = QApplication.primaryScreen()
        size = screen.availableGeometry()
        w = int(size.width() * 0.9)
        h = int(size.height() * 0.8)
        self.resize(w, h)
        self.cal = cal()
        self.user = user

        # Menu Bar client et fournisseur
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)
        gestion_menu = QMenu("Gestion des Tiers", self)
        menu_bar.addMenu(gestion_menu)
        client_action = gestion_menu.addAction("Clients")
        fournisseur_action = gestion_menu.addAction("Fournisseurs")
        client_action.triggered.connect(self.open_clients_dialog)
        fournisseur_action.triggered.connect(self.open_fournisseurs_dialog)
        # Centrer la fenêtre

        screen = QApplication.primaryScreen().availableGeometry()
        # Taille proportionnelle
        self.resize(int(screen.width() * 0.85), int(screen.height() * 0.85))
        # Centrage simple et fiable
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2
        )
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        # Root container
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(root)
        # Content area
        self.app_content = QStackedWidget()
        # Sidebar
        sidebar = self._create_sidebar()
        root_layout.addWidget(sidebar)
        # Main content
        self.app_stoct = StockApp(db_connection=db_path,user=self.user)
        self.app_content.addWidget(self.app_stoct)  
        self.app_pices  = ListePiece(db_path,user=self.user)
        self.app_content.addWidget(self.app_pices)
        self.app_caisse = SuiviTresorerie(db_path,user=self.user)
        self.app_content.addWidget(self.app_caisse)
        self.manager = RapportManager(db_path)
        facture, ventes = self.manager.load_data_from_sqlite()
        self.app_content.addWidget(RapportWindow(facture, ventes, db_path))
        root_layout.addWidget(self.app_content, 1)
    # Styles
        self._apply_styles()
    #  Connexions
        sidebar_widget = sidebar.findChild(QListWidget, "NavList")
        if sidebar_widget is None:
            return
        sidebar_widget.currentRowChanged.connect(self.app_content.setCurrentIndex)
        self.statusBar().showMessage(f"Connecté en tant que : {self.user}")
    # ---------------------------
    # UI Builders
    # ---------------------------
    def _create_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(9, 9, 9, 9)
        layout.setSpacing(10)
        # Navigation
        nav = QListWidget()
        nav.setFixedHeight(250)
        nav.setFixedWidth(260)
        nav.setObjectName("NavList")
        nav.setSpacing(8)
        nav.setFrameShape(QFrame.Shape.NoFrame)
        nav.setStyleSheet("QListWidget::item { height: 40px; font-size: 14px; font-family: 'Arial black'; }")

        style = QApplication.style()
        items = [
            ("Gestion des Articles", QIcon(":/icon/article.png")),
            ("Gestion des Ventes", QIcon(":/icon/facture_achat.png")),
            ("Gestion des Caisses", QIcon(":/icon/point-of-sale.png")),
            ("Tableau de Bord", QIcon(":/icon/parametres-du-graphique.png"))
        ]
        for text, icon in items:
            it = QListWidgetItem(icon, text)
            nav.addItem(it)
        nav.setCurrentRow(0)
        layout.addWidget(nav)
        # Spacer
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        # Settings/help
        btn_settings = QPushButton("Paramètres")
        btn_settings.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        btn_settings.setObjectName("SidebarButton")
        btn_settings.clicked.connect(self.open_settings)
        btn_help = QPushButton("Aide")
        btn_help.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        btn_help.setObjectName("SidebarButton")
        layout.addWidget(btn_settings)
        layout.addWidget(btn_help)
        return sidebar
    
    def open_settings(self):
        self.op_ = SetupWizardTabs(db_path,db_logo)
        self.op_.exec()

    def open_clients_dialog(self):
        dialog = TiersWidget(dbfolder=db_path, mode='Client')
        dialog.exec()

    def open_fournisseurs_dialog(self):
        dialog = TiersWidget(dbfolder=db_path, mode='Fournisseur')
        dialog.exec()
    # ---------------------------
    # Styles
    # ---------------------------
    def _apply_styles(self):
        with open("config/style.qss", "r", encoding="utf-8") as f:
            style = f.read()
            self.setStyleSheet(style)
    
    def closeEvent(self, event):

        logout(self.user, db_path)
        event.accept()

app = QApplication(sys.argv)
login = LoginWindow(db_path)

if login.exec() == QDialog.Accepted:
    user_id = login.user_id
    username = login.user
    print(username)
    main_win = StockWindow(username)
    main_win.show()
    sys.exit(app.exec())

# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     win = StockWindow()
#     win.show()
#     app.exec()
