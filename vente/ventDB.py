from datetime import datetime
from logging import log
from PySide6.QtWidgets import QMessageBox
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

    def fetch_data_as_dataframe(self, query: str) -> pd.DataFrame:
        conn = self.get_connection()

        try:
            df = pd.read_sql_query(query, conn)
            return df
        finally:
            conn.close()
    
    # Charger la liste des produits en stock avec quantité > 0
    def get_liste_produit(self):
        conn = self.get_connection()
        if not conn:
            print("Database connection failed.")
            return []
        try:
            cur = conn.cursor()
            query = '''
                    SELECT p.name, s.id_libelle, s.price_vente 
                    FROM stock s LEFT JOIN products p ON p.ref = s.id_libelle
                    WHERE s.qty > 0
                '''
            cur.execute(query)
            rows = cur.fetchall()
            conn.close()
            return rows
        except Exception as e:
            print(f"Error fetching product list: {e}")
            return []
        finally:
            conn.close()

    #  Recupérer les informations des clients
    def get_liste_client(self):
        conn = self.get_connection()
        if not conn:
            print("Database connection failed.")
            return []
        try:
            cur = conn.cursor()
            query = '''
                    SELECT id, nom FROM client WHERE type = 'Client'
                '''
            cur.execute(query)
            rows = cur.fetchall()
            conn.close()
            return rows
        except Exception as e:
            print(f"Error fetching client list: {e}")
            return []
        finally:
            conn.close()
    
    # Récupérer les remarques depuis la table infov
    def get_data_remaeque(self):
        conn = self.get_connection()
        if not conn:
            print("Database connection failed.")
            return []
        cur = conn.cursor()
        cur.execute("SELECT remarque FROM infov")
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]
    
    # Récupérer le stock disponible pour un code produit donné
    def get_stock_dispo(self, code):
        try:
            conn = self.cal.connect_to_db(self.dbfolder)
            if conn is None:
                return 0
            cur = conn.cursor()
            cur.execute("SELECT IFNULL(qty,0) FROM stock WHERE id_libelle=?", (code,))
            res = cur.fetchone()
            conn.close()
            return res[0] if res and res[0] is not None else 0
        except Exception:
            return 0
    
    def _save_devis_commande(self, cur, L, data_vente):
        """Traitement pour devis ou commande"""
        print(L)
        for e in data_vente.get("line_items", []):
            cur.execute(
                """INSERT INTO liste (client,code,facture,libelle,prix,quantite,montant,datee,id_clt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (e[0], e[1], e[2], e[3], e[4], e[5], e[6], e[7], e[8])
            )

        cur.execute(
            """INSERT INTO infov (factu, client, montant, mnt_ttc, payer, monn, datee,
                                statut_piece,statut_paiement, type_fact, remarque, utilisateur)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            L
        )

    
    
    def Info(self, factu):
        try:
            var_dic_vente = {}
            conn = self.cal.connect_to_db(self.dbfolder)
            if conn is None:
                return
            cur = conn.cursor()
            pr_v = '''SELECT * from infov where factu=?'''
            cur.execute(pr_v, [factu])
            cv = cur.fetchone()
            if cv:
                self.tva = float(cv[9]) if len(cv) > 9 else 0.0
                self.date = cv[6] if len(cv) > 6 else ""
                self.facto = cv[0]
                self.montant_verse = cv[4]
                self.reste = cv[5]
                self.type_fact = cv[9] if len(cv) > 9 else ""
                self.remarque = cv[11] if len(cv) > 11 else ""
                info = '''SELECT nom,cont,adr,ville from client where id=?'''
                cur.execute(info, [cv[1]])
                info_clt = cur.fetchone()
                if info_clt:
                    self.nom_clt = info_clt[0]
                    self.contact1 = info_clt[1]
                    self.adresse1 = info_clt[2]
                    self.ville = info_clt[3]

                var_dic_vente = {"Adrresse": self.adresse1,
                                 "Contact": self.contact1,
                                 "date": self.date,
                                 "facture": self.facto,
                                 "tva": self.tva,
                                 "ville": self.ville,
                                 "nom": self.nom_clt,
                                 "mont_verse": self.montant_verse,
                                 "reste": self.reste,
                                 "type_facture": self.type_fact,
                                 "remarque": self.remarque
                                 }
                conn.close()
            else:
                QMessageBox.warning(None, "Erreur", "Veuillez d'abord enregistrer la pièce")
            return var_dic_vente
        except Exception as e:
            log.error(f"Une erreur est survenue: {str(e)} dans Info")
            QMessageBox.warning(None, "Erreur", f"{e} dans Info")
    
    def type_paiement(self, mode_paiement, num_facture):
        moyen = self.cal.code_paiement(mode_paiement)
        moyen_ = f"{moyen}-{num_facture}"
        return moyen_
    
    def valeur_pour_db(self,valeur, defaut):
        return valeur if valeur is not None else defaut
    
    def get_data_by(self, id_clt, nom_clt, table, date_edit, num_line):
        id_clt = self.valeur_pour_db(id_clt, "client")
        nmclt = self.valeur_pour_db(nom_clt, "Client Ordinaire")
        factu = num_line
        # Support QDateTimeEdit, datetime, or string inputs
        if hasattr(date_edit, "date"):
            dat = date_edit.date().toString("yyyy-MM-dd")
            dat = datetime.strptime(dat, "%Y-%m-%d")
        elif isinstance(date_edit, datetime):
            dat = date_edit
        elif isinstance(date_edit, str):
            # Try common formats; fall back to raw string if parsing fails
            try:
                dat = datetime.strptime(date_edit, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    dat = datetime.strptime(date_edit, "%Y-%m-%d")
                except ValueError:
                    dat = date_edit
        else:
            dat = date_edit
        data_vente = {"line_items": []}
        for row in range(table.rowCount()):
            if not table.item(row, 0):
                continue

            code_item = table.item(row, 0)
            if code_item is None:
                continue
            code = code_item.text()
            prd_item = table.item(row, 1)
            if prd_item is None:
                continue
            prd = prd_item.text()
            qte = float(table.cellWidget(row, 2).value())
            pri = float(table.cellWidget(row, 3).value())
            mnt_item = table.item(row, 4)
            mnt = float(mnt_item.text()) if mnt_item is not None else pri * qte

            
            row_data = [nmclt, code, factu, prd, pri, qte, mnt, dat, id_clt]
            data_vente["line_items"].append(row_data)

        return data_vente
    
    def _save_facture(self, cur, L, mode_paiement, data_vente, user,
                  numero="", date_emission=None):

        montant_ht_total = 0.0

        # 🔹 Lignes de vente + stock
        for e in data_vente.get("line_items", []):
            cd = e[1]
            qte = e[5]
            prix_unitaire = e[4]
            montant_ht_total += prix_unitaire * qte

            cur.execute("""
                INSERT INTO vent (client, code, facture, libelle, prix, quantite,
                                montant, datee, id_clt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (e[0], e[1], e[2], e[3], e[4], e[5], e[6], e[7], e[8]))

            cur.execute(
                "UPDATE stock SET qty = qty - ? WHERE id_libelle = ?",
                (qte, cd)
            )

        # 🔹 Trésorerie (EXISTANT)
        if L[7] in ("Payé", "Avance"):
            if mode_paiement != "Moyen de paiement":
                if mode_paiement == "Espèces":
                    typ_compte = "Caisse"
                elif mode_paiement == "Mobile money":
                    typ_compte = "Compte Mobile"
                else:
                    typ_compte = "Banque"

                self.cal.insert_tresorerie(
                    cur=cur,
                    date_op=date_emission,
                    libelle="Vente",
                    montant=montant_ht_total,
                    type_op="ENTREE",
                    compte=typ_compte,
                    num=numero,
                    current_user=user
                )

        # 🔹 Insertion FACTURE (EXISTANT)
        cur.execute("""
            INSERT INTO infov
            (factu, client, montant, mnt_ttc, payer, monn,
            datee, statut_piece,statut_paiement, type_fact, remarque, utilisateur)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, L)

        
    
    def get_client_by_id(self,id_clt,date,facto,tva,montant_verse,reste,type_fact,remarque):
        conn = self.get_connection()
        rows = {}
        if not conn:
            print("Database connection failed.")
            return {}
        try:
            cur = conn.cursor()
            query = '''
                    SELECT nom,cont,adr,ville from client where id=?
                '''
            cur.execute(query,[id_clt])
            info_clt = cur.fetchone()
            if info_clt:
                rows = {
                "nom" : info_clt[0],
                "Contact" : info_clt[1],
                "adresse1" : info_clt[2],
                "ville" : info_clt[3],
                "date": date,
                "facture": facto,
                "tva": tva,
                "mont_verse": montant_verse,
                "reste": reste,
                "type_facture": type_fact,
                "remarque": remarque
                }
                return rows
            else:
                pass
        finally:
            conn.close()
    
    def get_facture_by_numero(self,cur,numero):
        """
        Docstring pour get_facture_by_numero
        
        :param self: Description
        :param cur: connexion
        :param numero: numero de la piece
        """
        cur.execute("""
            SELECT factu, mnt_ttc, payer, statut_piece, type_fact FROM infov WHERE factu =?
        """,(numero,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "numero":row[0],
            "type_piece":row[4],
            "statut":row[3],
            "montant":row[1],
            "versement":row[2],
        }