# auteur: zongo soumaïla
# Tel: +226 54267778 / 70925613
from interface.piece_ui import Ui_creer_piece_moderne
from PySide6.QtWidgets import QMessageBox, QDialog
from PySide6.QtCore import Signal



class choixPiece(QDialog):
    pieceChoisie = Signal(str)
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_creer_piece_moderne()
        self.ui.setupUi(self)
        # self.mode = mode
        # self.current_user = current_user  # <<< utilisateur connecté passé depuis login
        
        self.type_piece =None
        
        self.ui.pushButton.clicked.connect(self.validateSelection)

    

    def validateSelection(self):
        # Mapping radio → code
        mapping = {
            self.ui.radio_devis: "DV",
            self.ui.radio_commande: "CM",
            self.ui.radio_livraison: "BL",
            self.ui.radio_facture: "FAC"
        }

        self.type_piece = None

        for radio, code in mapping.items():
            if radio.isChecked():
                self.type_piece = code
                break

        if not self.type_piece:
            QMessageBox.information(
                self,
                "Attention",
                "Veuillez sélectionner un type de pièce."
            )
            return

        # Émettre UNE seule fois
        self.pieceChoisie.emit(self.type_piece)

        # Fermer proprement le dialog
        self.accept()
    def getSelectedPiece(self):
        return self.type_piece