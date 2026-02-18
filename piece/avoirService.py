import datetime
from decimal import Decimal
from fonction.methode  import cal
from fonction.methode import Numeroteur
class AvoirService:

    def __init__(self, db_path, user):
        self.db_path = db_path
        self.numeroteur = Numeroteur(db_path)
        self.user = user
        self.cal = cal()

    # ==========================================================
    # CREATION AVOIR
    # ==========================================================
    def creer_avoir(self, facture_id, lignes):

        conn = self.cal.connect_to_db(self.db_path)
        if conn is None:
            raise Exception("Connexion base impossible")

        cur = conn.cursor()

        try:
            conn.execute("BEGIN IMMEDIATE")

            # 🔹 Charger facture
            cur.execute("""
                SELECT factu, client, mnt_ttc
                FROM infov
                WHERE factu = ?
                AND type_fact = 'Facture'
            """, (facture_id,))
            facture = cur.fetchone()

            if not facture:
                raise Exception("Facture introuvable")

            ref_facture, client, montant_facture = facture
            montant_facture = Decimal(str(abs(montant_facture)))

            # 🔹 Calcul total avoir
            total_avoir = Decimal("0")

            for l in lignes:
                qty = Decimal(str(l["qty"]))
                price = Decimal(str(l["price"]))
                total_avoir += qty * price

            total_avoir = -abs(total_avoir)

            if total_avoir == 0:
                raise Exception("Montant avoir nul")

            # 🔹 Numéro avoir
            num_avoir = self.numeroteur.generer("AV", conn=conn, cur=cur)

            # 🔹 Insertion avoir (entête)
            cur.execute("""
                INSERT INTO infov (
                    factu, client, montant, mnt_ttc,
                    payer, monn, datee,
                    statut, type_fact, remarque,
                    utilisateur, origine
                )
                VALUES (?, ?, ?, ?, 0, 0, ?,
                        'AVOIR', 'AVOIR', ?, ?, ?)
            """, (
                num_avoir,
                client,
                float(total_avoir),
                float(total_avoir),
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                f"Avoir sur facture {ref_facture}",
                self.user,
                ref_facture
            ))

            # 🔹 Insertion lignes + stock
            for l in lignes:
                qty = Decimal(str(l["qty"]))
                price = Decimal(str(l["price"]))
                product_id = l["product_id"]

                # Ligne avoir
                cur.execute("""
                    INSERT INTO liste (facture, code, quantite, prix)
                    VALUES (?, ?, ?, ?)
                """, (
                    num_avoir,
                    product_id,
                    float(-abs(qty)),
                    float(price)
                ))

                # Réintégration stock
                cur.execute("""
                    UPDATE stock
                    SET qty = qty + ?
                    WHERE id_libelle = ?
                """, (
                    float(qty),
                    product_id
                ))

            # 🔹 Vérifier annulation facture
            self._verifier_annulation_facture(ref_facture, cur)

            # 🔹 Recalcul solde facture
            self._recalculer_solde_facture(ref_facture, cur)

            conn.commit()
            return num_avoir

        except Exception as e:
            conn.rollback()
            raise e

        finally:
            conn.close()

    # ==========================================================
    # ANNULATION AUTO SI 100%
    # ==========================================================
    def _verifier_annulation_facture(self, ref_facture, cur):

        cur.execute("""
            SELECT mnt_ttc
            FROM infov
            WHERE factu = ?
            AND type_fact = 'FACTURE'
        """, (ref_facture,))
        row = cur.fetchone()

        if not row:
            return

        montant_facture = Decimal(str(abs(row[0])))

        cur.execute("""
            SELECT COALESCE(SUM(mnt_ttc), 0)
            FROM infov
            WHERE origine = ?
            AND type_fact = 'AVOIR'
        """, (ref_facture,))
        total_avoirs = Decimal(str(abs(cur.fetchone()[0])))

        if total_avoirs >= montant_facture:
            cur.execute("""
                UPDATE infov
                SET statut = 'ANNULEE',
                    remarque = 'Facture annulée par avoir'
                WHERE factu = ?
            """, (ref_facture,))

    # ==========================================================
    # RECALCUL SOLDE
    # ==========================================================
    def _recalculer_solde_facture(self, ref_facture, cur):

        cur.execute("""
            SELECT mnt_ttc, payer
            FROM infov
            WHERE factu = ?
            AND type_fact = 'FACTURE'
        """, (ref_facture,))
        row = cur.fetchone()

        if not row:
            return

        montant_facture = Decimal(str(abs(row[0])))
        deja_paye = Decimal(str(row[1] or 0))

        cur.execute("""
            SELECT COALESCE(SUM(mnt_ttc), 0)
            FROM infov
            WHERE origine = ?
            AND type_fact = 'AVOIR'
        """, (ref_facture,))
        total_avoirs = Decimal(str(abs(cur.fetchone()[0])))

        solde = montant_facture - deja_paye - total_avoirs

        if solde > 0:
            statut = "PARTIELLE"
        elif solde == Decimal("0"):
            statut = "SOLDEE"
        else:
            statut = "TROP-PERCU"

        cur.execute("""
            UPDATE infov
            SET monn = ?, statut = ?
            WHERE factu = ?
        """, (
            float(solde),
            statut,
            ref_facture
        ))
