from fonction.methode import cal

class TresorerieRepository:
    def __init__(self, db_path):
        self.db_path = db_path

    def _connect(self):
        conn = cal.connect_to_db(self.db_path)
        if conn is None:
            raise RuntimeError("Connexion base impossible")
        return conn

    def get_all(self):
        with self._connect() as conn:
            return conn.execute("""
                SELECT date_operation, type, libelle, montant, compte
                FROM tresorerie
                ORDER BY date_operation DESC
            """).fetchall()

    def get_filtered(self, date_from, date_to, compte=None):
        query = """
            SELECT date_operation, libelle, type, montant, compte
            FROM tresorerie
            WHERE date_operation BETWEEN ? AND ?
        """
        params = [date_from, date_to]

        if compte:
            query += " AND compte = ?"
            params.append(compte)

        query += " ORDER BY date_operation ASC, id ASC"

        with self._connect() as conn:
            return conn.execute(query, params).fetchall()

    def resume_par_compte(self):
        with self._connect() as conn:
            return conn.execute("""
                SELECT compte,
                       SUM(CASE WHEN type='ENTREE' THEN montant ELSE 0 END),
                       SUM(CASE WHEN type='SORTIE' THEN montant ELSE 0 END)
                FROM tresorerie
                GROUP BY compte
            """).fetchall()
