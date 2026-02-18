# vente/infrastructure/facture_repository.py
class FactureRepository:

    def __init__(self, dbsource, numeroteur, cal):
        self.dbsource = dbsource
        self.numeroteur = numeroteur
        self.cal = cal

    def save_piece(
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
        conn = self.cal.connect_to_db(self.dbsource.dbfolder)
        cur = conn.cursor()

        try:
            conn.execute("BEGIN IMMEDIATE")

            from vente.domain.facture import Facture

            facture = Facture(
                id_client=id_clt,
                numero=numero,
                date_facture =date_edit,
                montant_ht=montant_ht,
                montant_verse=montant_verse,
                tva=tva,
                piece=piece,
                etat_paiement=etat_paiement,
                remarque=remarque,
                current_user=current_user,
                etat=etat_piece
            )

            L = facture.to_list()

            data_vente = self.dbsource.get_data_by(
                id_clt,
                nom_clt,
                table_widget,
                date_edit,
                numero
            )

            if piece == "Facture":
                self.dbsource._save_facture(
                    cur,
                    mode_paiement=mode_paiement,
                    L=L,
                    data_vente=data_vente,
                    numero=numero,
                    date_emission=date_edit,
                    user=current_user
                )
            else:
                self.dbsource._save_devis_commande(cur, L, data_vente)

            conn.commit()

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
