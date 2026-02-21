# auteur: zongo soumaïla
# Tel: +226 56832442 / 70925613
import json
import os
from PySide6.QtWidgets import QDoubleSpinBox,QComboBox,QTableWidget
import re
import sqlite3 as sq
from PySide6.QtCore import Qt,QSettings,QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
import datetime
import sys
import subprocess
CONFIG_FOLDER = 'config'

class cal:
    def __init__(self) -> None:
        super().__init__()
    
    @staticmethod  
    def connectioan(db_file):
        return cal.connect_to_db(db_file)
    # calcul de la remise
    def remis(self,ht:float,remis:float):
        try:
            remis = float(remis)
            ht = float(ht)
            mnt_remis = float(ht*(remis / 100))
            return mnt_remis
        except:
            pass
    #  calcul de la valeur ajoutee
    def tva(self,ht:float,tva:float):
        try:
            tva = float(tva)
            ht = float(ht)
            mnt_ttc =round(float(ht * (1 + (tva / 100))),2)
            return mnt_ttc
        except:
            pass
        
    # calcul de la valeur finale
    def net(self, taux_remis:float,taux_tva:float,mnt_ht:float):
        try:          

            mnt_ttc = (self.tva(mnt_ht,taux_tva))
            if mnt_ttc is None:
                return
            mnt_remis = (self.remis(mnt_ht,taux_remis))
            if mnt_remis is None:
                return
            net = (mnt_ttc) - mnt_remis
            return net
        except ValueError:
            pass
    def contact_validator(self,text):
        regex = QRegularExpression(r'^\+?\d{0,15}$')
        validator = QRegularExpressionValidator(regex,text) 
        return validator
    def contact_valid(self,contact:str):
        contact=str(contact)
        text_re=re.compile(r'^\+\d{11}$')
        if text_re.match(contact):
            return True
        else:
            return False 
    def recup_donnee(self,tab:QTableWidget):
        donne=[]
        for row in range(tab.rowCount()):
            row_data=[]
            for col in range(tab.columnCount()):
                item=tab.item(row,col) 
                if item:
                    row_data.append(item.text())
                
                elif tab.cellWidget(row,col):
                    widget=tab.cellWidget(row,col)
                    if isinstance(widget,QDoubleSpinBox):
                        row_data.append(str(widget.value()))
                    elif isinstance(widget,QComboBox):
                        dat = widget.currentData()
                        row_data.append(str(dat) if dat is not None else widget.currentText())
            donne.append(tuple(row_data))
        return donne
    
    def verifi_exit(self,tab:QTableWidget,item_exi):
        for ligne in range(tab.rowCount()):
            for col in range(tab.columnCount()):
                item=tab.item(ligne,col)
                if item and item.text()==item_exi:
                    return True
        return False
    
    def print_info(self,dbfolder): 
        try:
            conn = cal.connect_to_db(dbfolder)
            if conn is None:
                return
            cur = conn.cursor()
            sqls = '''SELECT * from infoentre'''
            cur.execute(sqls)
            resu = cur.fetchone()
            if resu:
                nom = resu[0]            
                tel = resu[1]
                tel1 = resu[2]
                detail = resu[3]
                nom_resp = resu[4]
                adr = resu[5]
                ville = resu[6]
                info ={"nom":nom,"T1":tel,"T2":tel1,"info":detail,"resp":nom_resp,"adresse":adr,"ville":ville,"ifu":resu[7],"autre":resu[8]}
                return info
            else:
                pass
        except Exception as e:
            pass
    
    def load_json(self):
        setting_file = os.path.join(CONFIG_FOLDER, "moyen.json")
        with open(setting_file,'r',encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def connect_to_db(db_file, timeout=30.0, row_factory=False):
        """
        Établit une connexion à la base de données SQLite.
        """
        try:
            conn = sq.connect(db_file, timeout=timeout)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 30000")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            if row_factory:
                conn.row_factory = sq.Row
            return conn
        except sq.Error:
            return None
    
    def extrait_data(self,table:QTableWidget):
        rows = table.rowCount()
        cols = table.columnCount()
        data = []
        for row in range(rows):
            rows_data ={}
            for col in range(cols):
                header = table.horizontalHeaderItem(col)
                if header is None:
                    return
                header = header.text()
                celle_values = table.item(row,col)
                if celle_values is None:
                    return
                celle_values = celle_values.text()
                rows_data[header] = celle_values
            data.append(rows_data)
        
        return data
    
    def nom_upper(self,text: str):
        word = text.split()
        if len(word) >= 2:
            text_format = word[0].upper() + " " + word[1].capitalize()
        elif len(word) == 1:
            text_format = word[0].upper()
        else:
            text_format = ""
        return text_format

    def code_paiement(self,methode:str) ->str:
        """Return the payment code based on the payment method.

            Args:
                methode (str): The payment method.

            Returns:
                str: The payment code, which is the first two uppercase characters of the stripped payment method.
                     Returns an empty string if the payment method is None or empty.
            """
        return methode.strip()[:2].upper() if methode else ""
    
        
    def charger_configuration_paie(self):
        """Charge la configuration depuis un fichier JSON."""
        setting_file = os.path.join(CONFIG_FOLDER, 'config_paie.json')
        
        try:
            with open(setting_file, "r") as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            pass
    
    def charger_tva_devise(self,db_file):
        """Charge la configuration depuis un fichier JSON."""
        
        try:
            conn = cal.connect_to_db(db_file)
            if conn is None:
                return
            cur = conn.cursor()
            sqls = '''SELECT * from config'''
            cur.execute(sqls)
            resu = cur.fetchone()
            
            if resu:
                date_debu = resu[0]            
                date_fin = resu[1]
                devise=resu[2]
                tva=resu[3]
                
                
                info={"date_debu":date_debu,"date_fin":date_fin,"devise":devise,"tva":tva}
                return info
            
        except FileNotFoundError:
            pass
    
    def insert_tresorerie(self,cur, date_op, libelle, montant, type_op, compte,num,current_user):
        """
        Enregistre l'opération de trésorerie simple.
        
        type_op doit être 'ENTREE' ou 'SORTIE'.
        compte doit être 'Caisse' ou 'Banque' ou 'Mobile Money'.
        """
        
        
        try:
            cur.execute("""
                INSERT INTO tresorerie (date_operation, libelle, montant, type, compte, reference, utilisateur)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (date_op, libelle, montant, type_op, compte, num, current_user))
           
            return True
        except sq.Error as e:
            print(e)
            return False
        

    def separateur_milieur(self,solde):
        return  f"{solde:,.2f}".replace(","," ").replace(".",",")

    
    def get_logo_path(self,cur):
        
        cur.execute("SELECT valeur FROM dossier WHERE cle='logo_path'")
        row = cur.fetchone()

        if row and os.path.exists(row[0]):
            return row[0]

        return None
    def get_sign_path(self,cur):
        
        cur.execute("SELECT valeur FROM dossier WHERE cle='signature_path'")
        row = cur.fetchone()

        if row and os.path.exists(row[0]):
            return row[0]

        return None
    def get_cach_path(self,cur):
        
        cur.execute("SELECT valeur FROM dossier WHERE cle='cachet_path'")
        row = cur.fetchone()
        if row and os.path.exists(row[0]):
            return row[0]
        return None

    def ensure_assets_dirs(self):
        base = os.path.join(os.path.dirname(__file__), "assets")
        for d in ["logo", "signature", "cachet"]:
            os.makedirs(os.path.join(base, d), exist_ok=True)
        return base

    def ouvrir_pdf(self, chemin_pdf):
        if not os.path.exists(chemin_pdf):

            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(chemin_pdf)   # Windows
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", chemin_pdf])  # macOS
            else:
                subprocess.Popen(["xdg-open", chemin_pdf])  # Linux
        except Exception as e:
            print("❌ ERREUR PDF :", e)
            raise

import datetime
class Numeroteur:
    def __init__(self, db):
        self.db = db
        self.cal = cal()
        self._init_db()
    
    def _init_db(self):
        self.conn = self.cal.connect_to_db(self.db)
        if self.conn is None:
            return False
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS numerotation (
            type_piece TEXT PRIMARY KEY,      -- FAC, AV, BL, DV…
            prefixe TEXT NOT NULL,             -- FAC, AV, BL…
            separateur TEXT DEFAULT '-',       -- -, /, _
            longueur INTEGER DEFAULT 3,        -- 001, 0001…
            reset_mode TEXT DEFAULT 'ANNUEL',  -- AUCUN | ANNUEL | MENSUEL
            compteur INTEGER DEFAULT 0,        -- compteur courant
            annee INTEGER,                     -- dernière année utilisée
            mois INTEGER                       -- dernier mois utilisé
        );

        """)
        cur.executemany("""
        INSERT OR IGNORE INTO numerotation
        (type_piece, prefixe, separateur, longueur, reset_mode)
        VALUES (?, ?, ?, ?, ?)
    """, [
        ('FAC', 'FAC', '-', 3, 'ANNUEL'),
        ('AV',  'AV',  '-', 3, 'ANNUEL'),
        ('BL',  'BL',  '-', 3, 'ANNUEL'),
        ('DV',  'DV',  '-', 3, 'ANNUEL'),
        ('CMD','CMD','-',3,'ANNUEL')
    ])
        self.conn.commit()
    def _get_cfg(self, type_piece, cur=None):
        own_conn = None
        if cur is None:
            own_conn = self.cal.connect_to_db(self.db)
            if own_conn is None:
                return
            cur = own_conn.cursor()
        cur.execute("""
            SELECT prefixe, separateur, longueur,
                   reset_mode, compteur, annee, mois
            FROM numerotation WHERE type_piece=?
        """, (type_piece,))
        row = cur.fetchone()
        if own_conn is not None:
            own_conn.close()
        return row

    def preview(self, type_piece):
        cfg = self._get_cfg(type_piece)
        if not cfg:
            return "NON CONFIGURÉ"

        prefixe, sep, lg, _, _, _, _ = cfg
        now = datetime.date.today()

        return f"{prefixe}{sep}{now.year}{sep}{now.month:02}{sep}{'X'*lg}"

    def generer(self, type_piece, conn=None, cur=None):
        own_conn = None
        if cur is None:
            own_conn = conn or self.cal.connect_to_db(self.db)
            if own_conn is None:
                return
            cur = own_conn.cursor()

        cfg = self._get_cfg(type_piece, cur=cur)
        if not cfg:
            raise ValueError("Numérotation non configurée")
        prefixe, sep, lg, reset, compteur, an, mois = cfg
        now = datetime.date.today()
        compteur = compteur or 0
        # 🔁 Gestion remise à zéro
        if reset == "ANNUEL" and an != now.year:
            compteur = 0
        elif reset == "MENSUEL" and (an != now.year or mois != now.month):
            compteur = 0

        compteur += 1

        numero = (
            f"{prefixe}{sep}"
            f"{now.year}{sep}{now.month:02}{sep}"
            f"{str(compteur).zfill(lg)}"
        )
        cur.execute("""
            UPDATE numerotation
            SET compteur=?, annee=?, mois=?
            WHERE type_piece=?
        """, (compteur, now.year, now.month, type_piece))
        if own_conn is not None:
            own_conn.commit()
            own_conn.close()

        return numero
    def generer_ref_produit(self, categorie):
        conn = self.cal.connect_to_db(self.db)
        if conn is None:
            return
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*) FROM products
            WHERE category = ?
        """, (categorie,))
        num = cur.fetchone()[0] + 1
        return f"{categorie[:3].upper()}-{str(num).zfill(4)}"

    def refer_client(self):
        conn = self.cal.connect_to_db(self.db)
        if conn is None:
            return
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*) FROM client where type='Client'
        """)
        num = cur.fetchone()[0] + 1
        return f"CL0-{str(num).zfill(3)}"
    def refer_fournisseur(self):
        conn = self.cal.connect_to_db(self.db)
        if conn is None:
            return
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*) FROM client where type='Fournisseur'
        """)
        num = cur.fetchone()[0] + 1
        return f"FR0-{str(num).zfill(3)}"
    def refe_caisse(self):
        conn = self.cal.connect_to_db(self.db)
        if conn is None:
            return
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*) FROM tresorerie
        """)
        num = cur.fetchone()[0] + 1
        return f"CAI-{str(num).zfill(3)}"
    
    def refe_inventaire(self):
        conn = self.cal.connect_to_db(self.db)
        if conn is None:
            return
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*) FROM inventory
        """)
        num = cur.fetchone()[0] + 1
        return f"INV-0{str(num).zfill(3)}"
# auteur: zongo soumaïla
# Tel: +226 56832442 / 70925613
