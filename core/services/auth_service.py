from datetime import datetime, timedelta

import bcrypt
from fonction.methode import cal
from fonction.model import hash_password


class AuthService:

    MAX_ATTEMPTS = 3
    LOCK_MINUTES = 5

    def __init__(self, db_path):
        self.db_path = db_path

    def login(self, username, password):

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, password, failed_attempts,
                   locked_until, actif
            FROM users
            WHERE username=?
        """, (username,))

        user = cur.fetchone()

        if not user:
            conn.close()
            return False, "Utilisateur introuvable"

        user_id, stored_pass, attempts, locked_until, actif = user

        if not actif:
            conn.close()
            return False, "Compte désactivé"

        # Vérifier verrouillage
        if locked_until:
            if datetime.now() < datetime.fromisoformat(locked_until):
                conn.close()
                return False, "Compte temporairement bloqué"

        # SQLite can return TEXT (str) or BLOB (bytes) depending on schema/data.
        stored_pass_bytes = stored_pass.encode("utf-8") if isinstance(stored_pass, str) else stored_pass

        if not bcrypt.checkpw(password.encode("utf-8"), stored_pass_bytes):

            attempts += 1
            # Verrouiller si dépassement
            if attempts >= self.MAX_ATTEMPTS:
                lock_time = datetime.now() + timedelta(minutes=self.LOCK_MINUTES)

                cur.execute("""
                    UPDATE users
                    SET failed_attempts=?,
                        locked_until=?
                    WHERE id=?
                """, (attempts, lock_time.isoformat(), user_id))
            # Sinon juste incrémenter les tentatives
            else:
                cur.execute("""
                    UPDATE users
                    SET failed_attempts=?
                    WHERE id=?
                """, (attempts, user_id))

            conn.commit()
            conn.close()
            return False, "Mot de passe incorrect",username
        # # Vérifier session déjà active
        # cur.execute("""
        #     SELECT is_connected
        #     FROM users
        #     WHERE id=?
        # """, (user_id,))

        # # Si déjà connecté ailleurs, refuser la connexion
        # if cur.fetchone()[0] == 1:
        #     conn.close()
        #     return False, "Utilisateur déjà connecté ailleurs",username
        # Succès
        cur.execute("""
            UPDATE users
            SET failed_attempts=0,
                locked_until=NULL,
                last_login=CURRENT_TIMESTAMP,
                is_connected=1
            WHERE id=?
        """, (user_id,))

        cur.execute("""
            INSERT INTO login_history (user_id, status)
            VALUES (?, 'SUCCESS')
        """, (user_id,))

        conn.commit()
        conn.close()

        return True, user_id,username
    
    # Déconnexion
    def logout(user_id, db_path):

        conn = cal.connect_to_db(db_path)
        cur = conn.cursor()

        cur.execute("""
            UPDATE users
            SET is_connected=0
            WHERE id=?
        """, (user_id,))

        cur.execute("""
            UPDATE login_history
            SET logout_time=CURRENT_TIMESTAMP
            WHERE user_id=? AND logout_time IS NULL
        """, (user_id,))

        conn.commit()
        conn.close()

def logout(user_id, db_path):
    return AuthService.logout(user_id, db_path)

