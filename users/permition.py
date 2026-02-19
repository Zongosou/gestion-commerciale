from fonction.methode import cal


class PermissionService:

    def __init__(self, db_path, user_id):
        self.db_path = db_path
        self.user_id = user_id

    def can(self, module, action):

        conn = cal.connect_to_db(self.db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT p.allowed
            FROM permissions p
            JOIN users u ON u.role_id = p.role_id
            WHERE u.id = ?
              AND p.module = ?
              AND p.action = ?
        """, (self.user_id, module, action))

        result = cur.fetchone()
        conn.close()

        return result and result[0] == 1
