import sqlite3
import pandas as pd
from fonction.methode import cal
class TresorerieService:

    @staticmethod
    def calculer_soldes(rows):
        solde = 0
        total_entrees = 0
        total_sorties = 0
        resultat = []
        

        for date, type_op, libelle, montant, compte in rows:
            montant = float(montant)
            type_op = type_op.upper().strip()

            if type_op == "ENTREE":
                solde += montant
                total_entrees += montant
            else:
                solde -= montant
                total_sorties += montant

            resultat.append((date, type_op, libelle, montant, compte, solde))

        return resultat, total_entrees, total_sorties, solde


class RapportManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.cal = cal()

    def _query(self, sql, params=()):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        return rows

    def ventes_mensuelles(self):
        return self._query("""
            SELECT strftime('%m', datee) as mois, SUM(montant)
            FROM infov
            WHERE type_fact='Facture'
            GROUP BY mois
            ORDER BY mois
        """)

    def ca_total(self):
        row = self._query("SELECT SUM(montant) FROM infov WHERE type_fact='Facture'")
        return row[0][0] if row and row[0][0] else 0

    def nb_factures(self):
        row = self._query("SELECT COUNT(*) FROM infov WHERE type_fact='Facture'")
        return row[0][0] if row else 0

    def panier_moyen(self):
        ca = self.ca_total()
        nb = self.nb_factures()
        return ca / nb if nb > 0 else 0

    def resume_tresorerie(self):
        return self._query("""
            SELECT 
                compte, 
                SUM(CASE WHEN type='ENTREE' THEN montant ELSE 0 END) as entree,
                SUM(CASE WHEN type='SORTIE' THEN montant ELSE 0 END) as sortie                
            FROM tresorerie
            GROUP BY compte
        """)
    # === CHARGEMENT DES DONNÉES ===
    def load_data_from_sqlite(self):
        conn = self.cal.connect_to_db(self.db_path)
        if conn is None:
            return pd.DataFrame(), pd.DataFrame()
        try:
            factures_df = pd.read_sql_query("""
                SELECT factu,montant,mnt_ttc,payer,monn,datee
                FROM infov WHERE type_fact = 'Facture'
            """, conn, parse_dates=["datee"])

            ventes_df = pd.read_sql_query("""
                SELECT client, libelle,sum(montant) as montant,datee
                FROM vent GROUP BY libelle
            """, conn, parse_dates=["datee"])
            conn.close()
            return factures_df, ventes_df
        except Exception as e:
            print(f"Erreur DB : {e}")
            return pd.DataFrame(), pd.DataFrame()
    def recharger_tresorie(self):
        return self._query("SELECT date_operation,type,libelle,montant,compte FROM tresorerie ORDER BY date_operation DESC")

