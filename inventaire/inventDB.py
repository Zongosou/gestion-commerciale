

import pandas as pd
from fonction.methode  import cal
class DBServiceMixin:
    def __init__(self, dbfolder: str):
        self.dbfolder = dbfolder
        self.cal = cal()

    def get_connection(self):
        return self.cal.connect_to_db(self.dbfolder)
    
class DataManageIn(DBServiceMixin):
    
    def get_all_invent(self):
        conn = self.get_connection()
        if conn is None:
            return 
        sql ='''
            SELECT 
                p.ref,
                p.name,
                COALESCE(s.qty,0) as qty
            FROM products p
            LEFT JOIN stock s ON s.id_libelle = p.ref
            ORDER BY p.name ASC
        '''
        df = pd.read_sql(sql, conn)
        conn.close()
        return df

    

 
  
    def get_inventory_items(self, inventory_id):
        conn = self.get_connection()
        if conn is None:
            return
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM inventory_items 
                WHERE inventory_id = ?
            """, (inventory_id,))
            rows = cur.fetchall()
        finally:
            conn.close()
        return rows
    
    

    def add_inventory_item(self, liste_donnees:list):
        conn = self.get_connection()
        if conn is None:
            return
        try:
            cur = conn.cursor()
            conn.execute("BEGIN IMMEDIATE")
            for ligne in liste_donnees:
                cur.execute("""
                    INSERT INTO inventory_items (inventory_id, product_ref, qty_theorique, qty_reelle, ecart) VALUES (?,?,?,?,?)
                """, (ligne))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def save_inventory_with_items(self, inventory_id, user, commentaire, valeur, statut, liste_donnees:list):
        conn = self.get_connection()
        if conn is None:
            return
        try:
            cur = conn.cursor()
            conn.execute("BEGIN IMMEDIATE")

            cur.execute("""
                INSERT INTO inventory (id, user, commentaire, valeur, statut)
                VALUES (?, ?, ?, ?, ?)
            """, (inventory_id, user, commentaire, valeur, statut))

            for ligne in liste_donnees:
                cur.execute("""
                    INSERT INTO inventory_items (inventory_id, product_ref, qty_theorique, qty_reelle, ecart)
                    VALUES (?, ?, ?, ?, ?)
                """, (ligne))

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def add_inventory_line(self, inventory_id, user, commentaire, valeur, statut):
        conn = self.get_connection()
        if conn is None:
            return
        try:
            cur = conn.cursor()
            conn.execute("BEGIN IMMEDIATE")
            cur.execute("""
                INSERT INTO inventory (id,user,commentaire,valeur,statut) VALUES (?,?,?,?,?)
            """, (inventory_id, user, commentaire, valeur, statut))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def load_inventories(self):
        conn = self.get_connection()
        if conn is None:
            return
        cur = conn.cursor()

        cur.execute("""
            SELECT id, date_inv, user, statut, commentaire,valeur,stock_corrige
            FROM inventory
            ORDER BY date_inv DESC
        """)

        rows = cur.fetchall()
        conn.close()

        return rows
    
    def get_inventory_by_index(self, index):
        conn = self.get_connection()
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("""
            SELECT  statut, stock_corrige
            FROM inventory
            ORDER BY date_inv DESC
            LIMIT 1 OFFSET ?
        """, (index,))
        row = cur.fetchone()
        staut= row[0]
        stock_corrige= row[1]
        conn.close()
        if row:
            return (staut, stock_corrige)
        return None
