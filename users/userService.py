from fonction.methode import cal
from fonction.model import hash_password


class UserService:

    def __init__(self, db_path):
        self.db_path = db_path

    def create_user(self, username, password, role_id, email=""):

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        hashed = hash_password(password)

        cur.execute("""
            INSERT INTO users (username, password, role_id, email)
            VALUES (?, ?, ?, ?)
        """, (username, hashed, role_id, email))

        conn.commit()
        conn.close()

    def update_user(self, user_id, role_id, actif):

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            UPDATE users
            SET role_id=?, actif=?
            WHERE id=?
        """, (role_id, actif, user_id))

        conn.commit()
        conn.close()

    def delete_user(self, user_id):

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        cur.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        conn.close()