class ValiderPieceUseCase:

    def __init__(self, dbsource, cal):
        self.dbsource = dbsource
        self.cal = cal

    def execute(self, numero_piece, current_user,new_statut):

        conn = self.cal.connect_to_db(self.dbsource.dbfolder)
        if conn is None:
            raise Exception("Connexion BD impossible")

        cur = conn.cursor()

        try:
            conn.execute("BEGIN IMMEDIATE")

            piece = self.dbsource.get_facture_by_numero(cur, numero_piece)

            if not piece:
                raise Exception("Pièce introuvable")

            type_piece = piece["type_piece"]
            statut_actuel = piece["statut"]

            if statut_actuel in ["Validé", "Validée"]:
                return

            from datetime import datetime
            date_validation = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 🔥 1️⃣ DEVIS / COMMANDE
            if type_piece in ["Devis", "Commande"]:

                cur.execute("""
                    UPDATE infov
                    SET statut_piece = ?,
                        date_validation = ?,
                        user_validation = ?
                    WHERE factu = ?
                """, (
                    new_statut,
                    date_validation,
                    current_user,
                    numero_piece
                ))

            # 🔥 2️⃣ BON DE LIVRAISON
            elif type_piece == "Bon de livraison":

                cur.execute("""
                    UPDATE infov
                    SET statut_piece = ?,
                        date_validation = ?,
                        user_validation = ?
                    WHERE factu = ?
                """, (
                    new_statut,
                    date_validation,
                    current_user,
                    numero_piece
                ))

                # impact stock
                # self.dbsource.generer_mouvement_stock(cur, numero_piece)

            # 🔥 3️⃣ FACTURE
            elif type_piece == "Facture":

                montant_ttc = float(piece["montant"])
                montant_verse = float(piece["versement"])

                from vente.vente_service import VenteService

                statut_paiement = VenteService.statut_paiement(
                    type_piece="Facture",
                    statut_piece=new_statut,
                    net=montant_ttc,
                    verse=montant_verse
                )

                cur.execute("""
                    UPDATE infov
                    SET statut_piece = ?,
                        statut_paiement = ?,
                        date_validation = ?,
                        user_validation = ?
                    WHERE factu = ?
                """, (
                    new_statut,
                    statut_paiement,
                    date_validation,
                    current_user,
                    numero_piece
                ))

                # impact stock si nécessaire
                # self.dbsource.generer_mouvement_stock(cur, numero_piece)

                # # comptabilité
                # self.dbsource.generer_ecriture_comptable(cur, numero_piece)

                # # trésorerie
                # if montant_verse > 0:
                #     self.dbsource.generer_mouvement_tresorerie(cur, numero_piece)

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise e

        finally:
            conn.close()
