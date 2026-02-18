# vente/application/creer_facture.py

from vente.domain.facture import Facture


class CreerFactureUseCase:

    def __init__(self, facture_repository):
        self.repo = facture_repository

    def execute(
        self,
        id_client,
        numero,
        date_facture,
        montant_ht,
        tva,
        montant_verse,
        remarque,
        piece,
        etat,
        current_user
    ):
        facture = Facture(
            id_client=id_client,
            numero=numero,
            date_facture=date_facture,
            montant_ht=montant_ht,
            tva=tva,
            montant_verse=montant_verse,
            remarque=remarque,
            piece=piece,
            etat=etat,
            current_user=current_user
        )

        return self.repo.save(facture)
