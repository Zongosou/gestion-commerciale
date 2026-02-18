
import sqlite3
from datetime import date

class ComptaService:

    def __init__(self, db_path):
        self.db_path = db_path

    def _get_param(self, cur, cle):
        cur.execute("SELECT valeur FROM parametres_compta WHERE cle=?", (cle,))
        r = cur.fetchone()
        return r[0] if r else None

    def _get_journal(self, cur, code):
        cur.execute("SELECT id, num_next FROM journaux WHERE code=?", (code,))
        return cur.fetchone()

    def _next_numero(self, cur, journal_id):
        cur.execute("UPDATE journaux SET num_next = num_next + 1 WHERE id=?", (journal_id,))

    def creer_ecriture(self, journal_code, libelle, reference, utilisateur, lignes):
        """
        lignes = [
          {"compte":"411000","debit":1000,"credit":0,"libelle":"Client"},
          {"compte":"701000","debit":0,"credit":1000,"libelle":"Vente"}
        ]
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        journal_id, num_next = self._get_journal(cur, journal_code)
        numero = f"{journal_code}{str(num_next).zfill(6)}"

        total_debit = sum(l.get("debit", 0) for l in lignes)
        total_credit = sum(l.get("credit", 0) for l in lignes)

        if round(total_debit, 2) != round(total_credit, 2):
            raise ValueError("Écriture non équilibrée")

        # Entête
        cur.execute("""
            INSERT INTO ecritures
            (journal_id, numero, datee, reference, libelle,
             total_debit, total_credit, statut, utilisateur)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'posted', ?)
        """, (
            journal_id, numero, date.today().isoformat(),
            reference, libelle, total_debit, total_credit, utilisateur
        ))

        ecriture_id = cur.lastrowid

        # Lignes
        for l in lignes:
            cur.execute("""
                INSERT INTO ecriture_lines
                (ecriture_id, compte_code, libelle, debit, credit)
                VALUES (?, ?, ?, ?, ?)
            """, (
                ecriture_id,
                l["compte"],
                l.get("libelle", ""),
                l.get("debit", 0),
                l.get("credit", 0)
            ))

        self._next_numero(cur, journal_id)

        conn.commit()
        conn.close()

        return numero
