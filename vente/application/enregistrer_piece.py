# vente/application/enregistrer_piece.py

class EnregistrerPieceUseCase:

    def __init__(self, repository):
        self.repo = repository

    def execute(
        self,
        piece,
        id_clt,
        nom_clt,
        table_widget,
        date_edit,
        numero,
        montant_ht,
        montant_verse,
        tva,
        remarque,
        current_user,
        etat_piece,
        etat_paiement,
        mode_paiement
    ):
        self.repo.save_piece(
            piece=piece,
            id_clt=id_clt,
            nom_clt=nom_clt,
            table_widget=table_widget,
            date_edit=date_edit,
            numero=numero,
            montant_ht=montant_ht,
            montant_verse=montant_verse,
            tva=tva,
            remarque=remarque,
            current_user=current_user,
            etat_piece=etat_piece,
            etat_paiement=etat_paiement,
            mode_paiement=mode_paiement
        )
