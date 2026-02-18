# vente/domain/facture.py

from datetime import datetime
from .calcul_vente import CalculVente


class Facture:

    def __init__(
        self,
        id_client: int,
        numero: str,
        date_facture: datetime,
        montant_ht: float = 0.0,
        tva: float = 0.0,
        montant_verse: float = 0.0,
        remarque: str = "",
        piece: str = "Facture",
        etat: str = "",
        etat_paiement: str = "",
        current_user: str = None
    ):
        self.numero = numero
        self.id_client = id_client
        self.date_facture = date_facture
        self.montant_ht = float(montant_ht or 0.0)
        self.tva = float(tva or 0.0)
        self.montant_verse = float(montant_verse or 0.0)
        self.remarque = remarque
        self.piece = piece
        self.etat = etat
        self.etat_paiement = etat_paiement
        self.current_user = current_user

        # Calcul automatique
        self.montant_ttc = CalculVente.calcul_ttc(self.montant_ht, self.tva)
        self.reste = CalculVente.calcul_reste(self.montant_ttc, self.montant_verse)

    def to_list(self):
        """
        Remplace ton ancienne Liste_donne
        """
        if self.piece == "Facture":
            return [
                self.numero,
                self.id_client,
                self.montant_ht,
                self.montant_ttc,
                self.montant_verse,
                self.reste,
                self.date_facture,
                self.etat,
                self.etat_paiement,
                self.piece,
                self.remarque,
                self.current_user
            ]
        else:
            # factu, client, montant, mnt_ttc, payer, monn, datee,
            #                     statut_piece,statut_paiement, type_fact, remarque, utilisateur)
            return [
                self.numero,
                self.id_client,
                self.montant_ht,
                self.montant_ttc,
                0.0,
                0.0,
                self.date_facture,
                self.etat,
                self.etat_paiement,
                self.piece,
                self.remarque,
                self.current_user
            ]
