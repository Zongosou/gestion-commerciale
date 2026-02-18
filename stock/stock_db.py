
from datetime import datetime

import pandas as pd
from fonction.methode  import cal
class DBServiceMixin:
    def __init__(self, dbfolder: str):
        self.dbfolder = dbfolder
        self.cal = cal()

    def get_connection(self):
        return self.cal.connect_to_db(self.dbfolder)
    
class DataManage(DBServiceMixin):
    def __init__(self, dbfolder: str):
        super().__init__(dbfolder)
        self.init_db()
    
    def init_db(self):
        conn = self.get_connection()
        if conn is None:
            return False
        cur = conn.cursor()

        # Table produits
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                ref INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                quantity INTEGER DEFAULT 0,
                price REAL DEFAULT 0,
                alert_min INTEGER DEFAULT 5,
                created_at TEXT
            )
        """)

        # Historique des ajustements
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                old_qty INTEGER,
                new_qty INTEGER,
                type TEXT,
                user TEXT,
                date TEXT,
                comment TEXT,
                FOREIGN KEY(product_id) REFERENCES products(ref)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS supplier_payment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                facture TEXT,
                montant REAL,
                user TEXT,
                date TEXT
            )
        """)

        self._migrate_stock_history_fk(cur)
        conn.commit()
        conn.close()

    def _migrate_stock_history_fk(self, cur):
        """
        Corrige les anciennes bases où stock_history pointait vers products(id)
        au lieu de products(ref), ce qui provoque un foreign key mismatch.
        """
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stock_history'")
        if not cur.fetchone():
            return

        cur.execute("PRAGMA foreign_key_list(stock_history)")
        fk_rows = cur.fetchall()
        must_migrate = any(row[2] == "products" and row[4] == "id" for row in fk_rows)
        if not must_migrate:
            return

        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock_history_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                old_qty INTEGER,
                new_qty INTEGER,
                type TEXT,
                user TEXT,
                date TEXT,
                comment TEXT,
                FOREIGN KEY(product_id) REFERENCES products(ref)
            )
        """)
        cur.execute("""
            INSERT INTO stock_history_new (id, product_id, old_qty, new_qty, type, user, date, comment)
            SELECT id, product_id, old_qty, new_qty, type, user, date, comment
            FROM stock_history
        """)
        cur.execute("DROP TABLE stock_history")
        cur.execute("ALTER TABLE stock_history_new RENAME TO stock_history")
    # Ajouter un nouveau produit
    def add_product(self,ref,name, category, quantity, price, price_vent, alert_min):
        conn = self.get_connection()
        if conn is None:
            return False
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO products (ref,name, category, price,price_vent, alert_min, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ref,name, category,  price, price_vent, alert_min, datetime.now().isoformat()))
        cur.execute("""
            INSERT INTO stock (id_libelle, qty,price,price_vente)
                    VALUES (?, ?, ?, ?)""", (ref, quantity, price, price_vent))
        conn.commit()
        conn.close()
    # Mettre à jour la quantité d'un produit
    def update_product(self, product_id, name, category, quantity,
                   price, price_vent, alert_min):

        conn = self.get_connection()
        if conn is None:
            return "ERROR"

        try:
            cur = conn.cursor()

            # 1️⃣ Mise à jour du produit
            cur.execute("""
                UPDATE products
                SET name = ?, category = ?, price = ?, price_vent = ?, alert_min = ?
                WHERE ref = ? AND actif = 1
            """, (name, category, price, price_vent, alert_min, product_id))

            # 2️⃣ Vérifier si le stock existe
            cur.execute("""
                SELECT COUNT(*) FROM stock WHERE id_libelle = ?
            """, (product_id,))
            exists = cur.fetchone()[0]

            if exists:
                # 3️⃣ Mise à jour du stock
                cur.execute("""
                    UPDATE stock
                    SET qty = qty+?, price = ?, price_vente = ?
                    WHERE id_libelle = ?
                """, (quantity, price, price_vent, product_id))
            else:
                # 4️⃣ Création du stock si absent
                cur.execute("""
                    INSERT INTO stock (id_libelle, qty, price, price_vente)
                    VALUES (?, ?, ?, ?)
                """, (product_id, quantity, price, price_vent))

            conn.commit()
            return "OK"

        except Exception as e:
            conn.rollback()
            print("Erreur update_product:", e)
            return "ERROR"

        finally:
            conn.close()


    # Récupérer tous les produits
    def get_all_products(self):
        conn = self.get_connection()
        if conn is None:
            return False
        cur = conn.cursor()

        cur.execute("""
            SELECT 
                p.ref,
                p.name,
                p.category,
                COALESCE(s.qty,0) as qty,
                p.price,
                p.price_vent,
                p.alert_min
            FROM products p
            LEFT JOIN stock s ON s.id_libelle = p.ref
            ORDER BY p.name ASC
        """)


        rows = cur.fetchall()
        
        conn.close()
        cols = ['ref','produit','categorie','qty','price','price_vent','alert_min']
        
        return [dict(zip(cols, r)) for r in rows]
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

    # Récupérer les produits en dessous du seuil d'alerte
    def get_low_stock_products(self):
        conn = self.get_connection()
        if conn is None:
            return False
        cur = conn.cursor()

        cur.execute("""
            SELECT ref, name, category, quantity, price, alert_min
            FROM products
            WHERE quantity <= alert_min
            ORDER BY quantity ASC
        """)

        rows = cur.fetchall()
        conn.close()
        return rows

    # Ajouter une entrée dans l'historique des ajustements
    def add_history(self,product_id, old_qty, new_qty, movement_type, user="SYSTEM", comment=""):
        conn = self.get_connection()
        if conn is None:
            return False
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO stock_history (product_id, old_qty, new_qty, type, user, date, comment)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (product_id, old_qty, new_qty, movement_type, user, datetime.now().isoformat(), comment))

        conn.commit()
        conn.close()

    def get_all_history(self):
        conn = self.get_connection()
        if conn is None:
            return False
        cur = conn.cursor()

        cur.execute("""
            SELECT h.date, p.name, h.old_qty, h.new_qty, h.type, h.user, h.comment
            FROM stock_history h
            JOIN products p ON p.ref = h.product_id
            ORDER BY h.date DESC
        """)

        rows = cur.fetchall()
        conn.close()
        return rows

    def get_entry_transactions_by_day(self):
        conn = self.get_connection()
        if conn is None:
            return False

        cur = conn.cursor()

        cur.execute("""
            SELECT
                DATE(h.date) AS day,
                COUNT(h.id) AS nb_transactions,
                SUM(
                    CASE
                        WHEN h.new_qty > h.old_qty
                        THEN (h.new_qty - h.old_qty)
                        ELSE 0
                    END
                ) AS qty_total,
                GROUP_CONCAT(h.user, ', ') AS users,
                GROUP_CONCAT(
                    p.name || ' x' || (h.new_qty - h.old_qty),
                    ' | '
                ) AS details
            FROM stock_history h
            JOIN products p ON p.ref = h.product_id
            WHERE UPPER(h.type) LIKE 'ENTR%'
            AND h.new_qty > h.old_qty
            GROUP BY DATE(h.date)
            ORDER BY DATE(h.date) DESC
        """)

        rows = cur.fetchall()
        conn.close()

        cols = ["day", "nb_transactions", "qty_total", "users", "details"]
        return [dict(zip(cols, r)) for r in rows]

    # Récupérer l'historique pour un produit spécifique
    def get_history_for_product(self,product_id):
        conn = self.get_connection()
        if conn is None:
            return False
        cur = conn.cursor()

        cur.execute("""
            SELECT h.date, p.name, h.old_qty, h.new_qty, h.type, h.user, h.comment
            FROM stock_history h
            JOIN products p ON p.ref = h.product_id
            WHERE product_id=?
            ORDER BY h.date DESC
        """, (product_id,))

        rows = cur.fetchall()
        conn.close()
        return rows

    # Récupérer un produit par son ID
    def get_product_by_id(self,pid):
        conn = self.get_connection()
        if conn is None:
            return False
        cur = conn.cursor()
        cur.execute("SELECT ref, name, category, price,price_vent, alert_min FROM products WHERE ref=?", (pid,))
        row = cur.fetchone()
        conn.close()
        return row

    def delete_product(self, product_id, user):
        conn = self.get_connection()
        if conn is None:
            return "ERROR"

        cur = conn.cursor()

        # Vérifier le stock
        cur.execute(
            "SELECT COALESCE(SUM(qty), 0) FROM stock WHERE id_libelle = ?",
            (product_id,)
        )
        qty = cur.fetchone()[0]

        if qty > 0:
            conn.close()
            return "STOCK_EXISTANT"

        # Historique
        cur.execute("""
            INSERT INTO product_history (product_ref, action, user)
            VALUES (?, 'DELETE', ?)
        """, (product_id, user))

        # Suppression logique
        cur.execute("""
            UPDATE products SET actif = 0 WHERE ref = ?
        """, (product_id,))

        conn.commit()
        conn.close()
        return "OK"

     
    def total_stock_value(self):
        conn = self.get_connection()
        if conn is None:
            return False
        cur = conn.cursor()
        cur.execute("SELECT SUM(quantity * price) FROM products")
        result = cur.fetchone()[0] or 0
        conn.close()
        return result

    def products_in_low_stock(self):
        conn = self.get_connection()
        if conn is None:
            return False
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM products WHERE quantity <= alert_min")
        result = cur.fetchone()[0]
        conn.close()
        return result

    def get_inventory_items(self, inventory_id):
        conn = self.get_connection()
        if conn is None:
            return
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM inventory_items 
            WHERE inventory_id = ?
        """, (inventory_id,))

        rows = cur.fetchall()
        
        conn.close()
        return rows

    def create_inventory(self, user, commentaire=""):
        conn = self.get_connection()
        if conn is None:
            return
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO inventory (user, commentaire)
            VALUES (?, ?)
        """, (user, commentaire))

        inventory_id = cur.lastrowid
        conn.commit()
        conn.close()
        return inventory_id
    
    

    def add_inventory_item(self, liste_donnees:list):
        conn = self.get_connection()
        if conn is None:
            return
        cur = conn.cursor()
        for ligne in liste_donnees:
            cur.execute("""
                INSERT INTO inventory_items (inventory_id, product_ref, qty_theorique, qty_reelle, ecart) VALUES (?,?,?,?,?)
            """, (ligne))
            
        conn.commit()
        conn.close()
    
    def add_inventory_line(self, inventory_id, user, commentaire, valeur, statut):
        conn = self.get_connection()
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO inventory (id,user,commentaire,valeur,statut) VALUES (?,?,?,?,?)
        """, (inventory_id, user, commentaire, valeur, statut))
        conn.commit()
        conn.close()

    def load_inventories(self):
        conn = self.get_connection()
        if conn is None:
            return
        cur = conn.cursor()

        cur.execute("""
            SELECT id, date_inv, user, statut, commentaire,valeur
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
    def get_supplier_debts_by_day(self):
        conn = self.get_connection()
        if conn is None:
            return []

        cur = conn.cursor()

        cur.execute("""
            SELECT 
                DATE(datee) as day,
                COUNT(factu) as nb_factures,
                SUM(montant) as total_achat,
                SUM(mnt_paye) as total_paye,
                SUM(montant - mnt_paye) as total_reste
            FROM info
            GROUP BY DATE(datee)
            ORDER BY DATE(datee) DESC
        """)

        rows = cur.fetchall()
        print(rows)
        conn.close()

        cols = [
            "day",
            "nb_factures",
            "total_achat",
            "total_paye",
            "total_reste"
        ]

        return [dict(zip(cols, r)) for r in rows]
# Récupérer les factures impayées d'un fournisseur spécifique ou de tous les fournisseurs
    def get_unpaid_supplier_invoices(self, supplier_id=None):
        conn = self.get_connection()
        if conn is None:
            return []

        cur = conn.cursor()

        if supplier_id:
            cur.execute("""
                SELECT factu, datee, montant, mnt_paye,
                    (montant - mnt_paye) as reste
                FROM info
                WHERE id_fr = ?
                AND (montant - mnt_paye) > 0
                ORDER BY datee DESC
            """, (supplier_id,))
        else:
            cur.execute("""
                SELECT factu, datee, montant, mnt_paye,
                    (montant - mnt_paye) as reste
                FROM info
                WHERE (montant - mnt_paye) > 0
                ORDER BY datee DESC
            """)

        rows = cur.fetchall()
        conn.close()

        cols = ["facture", "date", "montant", "paye", "reste"]
        return [dict(zip(cols, r)) for r in rows]

# Effectuer un paiement sur une facture fournisseur
    def pay_supplier_invoice(self, facture, montant_paye, user="SYSTEM"):
        conn = self.get_connection()
        if conn is None:
            return False

        try:
            cur = conn.cursor()
            conn.execute("BEGIN IMMEDIATE")

            # Récupérer données actuelles
            cur.execute("""
                SELECT montant, mnt_paye
                FROM info
                WHERE factu = ?
            """, (facture,))
            row = cur.fetchone()

            if not row:
                return False

            montant_total, deja_paye = row
            nouveau_paye = deja_paye + montant_paye

            if nouveau_paye > montant_total:
                return "DEPASSEMENT"

            # Update facture
            cur.execute("""
                UPDATE info
                SET mnt_paye = ?
                WHERE factu = ?
            """, (nouveau_paye, facture))

            # Historique paiement
            cur.execute("""
                INSERT INTO supplier_payment_history (
                    facture, montant, user, date
                )
                VALUES (?, ?, ?, ?)
            """, (
                facture,
                montant_paye,
                user,
                datetime.now().isoformat()
            ))

            conn.commit()
            return "OK"

        except Exception as e:
            conn.rollback()
            print("Erreur paiement:", e)
            return False

        finally:
            conn.close()
