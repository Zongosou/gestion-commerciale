from fonction.model import hash_password
from fonction.methode import cal


class AuthService:

    def __init__(self, db_path):
        self.db_path = db_path

    def login(self, username, password):

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, password, actif
            FROM users
            WHERE username=?
        """, (username,))

        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        if row[2] == 0:
            return None

        if hash_password(password) != row[1]:
            return None

        return {
            "id": row[0],
            "username": username
        }
