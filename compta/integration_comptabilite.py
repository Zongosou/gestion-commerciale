# integration_comptabilite.py

import json
import datetime
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import sqlite3
from abc import ABC, abstractmethod
import logging
from dataclasses import dataclass, field
from enum import Enum

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =====================================================================
# 1. MODÈLES DE DONNÉES
# =====================================================================

class TypeJournal(Enum):
    """Types de journaux comptables"""
    VENTES = "VT"
    ACHATS = "AC"
    BANQUE = "BN"
    CAISSE = "CA"
    OPERATIONS_DIVERSES = "OD"
    CLIENTS = "CL"
    FOURNISSEURS = "FR"

class TypeTiers(Enum):
    """Types de tiers"""
    CLIENT = "client"
    FOURNISSEUR = "fournisseur"
    SALARIE = "salarie"
    AUTRE = "autre"

@dataclass
class CompteComptable:
    """Modèle d'un compte comptable personnalisable"""
    code: str
    intitule: str
    classe: str  # 1-9 selon PCG
    type: str  # 'actif', 'passif', 'charge', 'produit'
    tiers_lie: Optional[TypeTiers] = None
    tva_applicable: bool = False
    taux_tva: Optional[float] = None
    actif: bool = True
    metadata: Dict = field(default_factory=dict)

@dataclass
class LigneEcriture:
    """Une ligne d'écriture comptable"""
    compte: str  # Code du compte
    libelle: str
    debit: Decimal
    credit: Decimal
    tiers_id: Optional[str] = None  # Référence client/fournisseur
    tiers_type: Optional[TypeTiers] = None
    analytique: Optional[str] = None  # Centre de coût/projet
    quantite: Optional[Decimal] = None  # Pour la comptabilité analytique

@dataclass
class EcritureComptable:
    """Écriture comptaire complète"""
    id: Optional[str] = None
    date = field(default_factory=date.today)
    journal: TypeJournal = TypeJournal.OPERATIONS_DIVERSES
    numero_piece: Optional[str] = None
    libelle: str = ""
    lignes: List[LigneEcriture] = field(default_factory=list)
    lettree: bool = False
    rapprochee: bool = False
    module_source: Optional[str] = None  # 'ventes', 'achats', 'depenses'
    reference_source: Optional[str] = None  # ID de la facture/commande source
    validee: bool = True
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)

@dataclass
class RegleComptabilisation:
    """Règle pour la génération automatique d'écritures"""
    id: str
    module_source: str  # 'vente', 'achat', 'depense', 'avoir', 'paiement'
    type_operation: str  # 'facture', 'avoir', 'paiement_client', 'paiement_fournisseur'
    conditions: Dict[str, Any]  # Conditions d'application
    comptes_defaut: Dict[str, str]  # Mapping compte par défaut
    comptes_personnalises: Dict[str, str] = field(default_factory=dict)  # Override par utilisateur
    actif: bool = True
    ordre: int = 100  # Ordre d'application

# =====================================================================
# 2. GESTIONNAIRE DU PLAN COMPTABLE (Personnalisable)
# =====================================================================

class GestionnairePlanComptable:
    """Gère le plan comptable personnalisé de l'entreprise"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or ":memory:"
        self.comptes = {}
        self._init_db()
        self._charger_comptes_par_defaut()
    
    def _init_db(self):
        """Initialise la base de données SQLite"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        # Table des comptes comptables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comptes (
                code TEXT PRIMARY KEY,
                intitule TEXT NOT NULL,
                classe TEXT NOT NULL,
                type TEXT NOT NULL,
                tiers_lie TEXT,
                tva_applicable BOOLEAN DEFAULT 0,
                taux_tva REAL,
                actif BOOLEAN DEFAULT 1,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table des règles de comptabilisation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS regles_comptabilisation (
                id TEXT PRIMARY KEY,
                module_source TEXT NOT NULL,
                type_operation TEXT NOT NULL,
                conditions TEXT NOT NULL,
                comptes_defaut TEXT NOT NULL,
                comptes_personnalises TEXT,
                actif BOOLEAN DEFAULT 1,
                ordre INTEGER DEFAULT 100
            )
        ''')
        
        self.conn.commit()
    
    def _charger_comptes_par_defaut(self):
        """Charge les comptes comptables par défaut (PCG français simplifié)"""
        comptes_defaut = [
            # Comptes de tiers
            ("401000", "Fournisseurs", "4", "passif", "fournisseur", False, None),
            ("411000", "Clients", "4", "actif", "client", False, None),
            ("419000", "Clients créditeurs", "4", "passif", "client", False, None),
            
            # Comptes de charges
            ("601000", "Achats stockés - Matières premières", "6", "charge", None, True, 20.0),
            ("606000", "Achats non stockés", "6", "charge", None, True, 20.0),
            ("607000", "Achats de marchandises", "6", "charge", None, True, 20.0),
            ("613000", "Locations", "6", "charge", None, True, 20.0),
            ("621000", "Personnel extérieur", "6", "charge", None, False, None),
            ("641000", "Rémunérations du personnel", "6", "charge", None, False, None),
            ("645000", "Charges sociales", "6", "charge", None, False, None),
            
            # Comptes de produits
            ("701000", "Ventes de produits finis", "7", "produit", None, True, 20.0),
            ("707000", "Ventes de marchandises", "7", "produit", None, True, 20.0),
            ("706000", "Prestations de services", "7", "produit", None, True, 20.0),
            
            # Comptes de TVA
            ("445660", "TVA déductible", "4", "actif", None, False, None),
            ("445710", "TVA collectée", "4", "passif", None, False, None),
            ("445510", "TVA à décaisser", "4", "passif", None, False, None),
            
            # Comptes financiers
            ("512000", "Banque", "5", "actif", None, False, None),
            ("530000", "Caisse", "5", "actif", None, False, None),
            ("571000", "Chèque à encaisser", "5", "actif", None, False, None),
        ]
        
        cursor = self.conn.cursor()
        for compte in comptes_defaut:
            cursor.execute('''
                INSERT OR IGNORE INTO comptes 
                (code, intitule, classe, type, tiers_lie, tva_applicable, taux_tva)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', compte)
        self.conn.commit()
        self._mettre_a_jour_cache()
    
    def _mettre_a_jour_cache(self):
        """Met à jour le cache en mémoire des comptes"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM comptes WHERE actif = 1")
        self.comptes = {}
        for row in cursor.fetchall():
            compte = CompteComptable(
                code=row['code'],
                intitule=row['intitule'],
                classe=row['classe'],
                type=row['type'],
                tiers_lie=TypeTiers(row['tiers_lie']) if row['tiers_lie'] else None,
                tva_applicable=bool(row['tva_applicable']),
                taux_tva=row['taux_tva'],
                actif=bool(row['actif']),
                metadata=json.loads(row['metadata']) if row['metadata'] else {}
            )
            self.comptes[compte.code] = compte
    
    def ajouter_compte(self, compte: CompteComptable) -> bool:
        """Ajoute ou modifie un compte comptable"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO comptes 
                (code, intitule, classe, type, tiers_lie, tva_applicable, taux_tva, actif, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                compte.code,
                compte.intitule,
                compte.classe,
                compte.type,
                compte.tiers_lie.value if compte.tiers_lie else None,
                1 if compte.tva_applicable else 0,
                compte.taux_tva,
                1 if compte.actif else 0,
                json.dumps(compte.metadata) if compte.metadata else None
            ))
            self.conn.commit()
            self._mettre_a_jour_cache()
            logger.info(f"Compte {compte.code} ajouté/modifié")
            return True
        except Exception as e:
            logger.error(f"Erreur ajout compte {compte.code}: {e}")
            return False
    
    def desactiver_compte(self, code_compte: str) -> bool:
        """Désactive un compte comptable"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE comptes SET actif = 0 WHERE code = ?", (code_compte,))
            self.conn.commit()
            self._mettre_a_jour_cache()
            logger.info(f"Compte {code_compte} désactivé")
            return True
        except Exception as e:
            logger.error(f"Erreur désactivation compte {code_compte}: {e}")
            return False
    
    def rechercher_comptes(self, filtre: Dict = None) -> List[CompteComptable]:
        """Recherche des comptes selon des critères"""
        query = "SELECT * FROM comptes WHERE 1=1"
        params = []
        
        if filtre:
            if 'classe' in filtre:
                query += " AND classe LIKE ?"
                params.append(f"{filtre['classe']}%")
            if 'type' in filtre:
                query += " AND type = ?"
                params.append(filtre['type'])
            if 'tiers_lie' in filtre:
                query += " AND tiers_lie = ?"
                params.append(filtre['tiers_lie'])
            if 'actif' in filtre:
                query += " AND actif = ?"
                params.append(1 if filtre['actif'] else 0)
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        
        comptes = []
        for row in cursor.fetchall():
            compte = CompteComptable(
                code=row['code'],
                intitule=row['intitule'],
                classe=row['classe'],
                type=row['type'],
                tiers_lie=TypeTiers(row['tiers_lie']) if row['tiers_lie'] else None,
                tva_applicable=bool(row['tva_applicable']),
                taux_tva=row['taux_tva'],
                actif=bool(row['actif']),
                metadata=json.loads(row['metadata']) if row['metadata'] else {}
            )
            comptes.append(compte)
        
        return comptes
    
    def get_compte_par_defaut(self, type_operation: str, role: str) -> Optional[str]:
        """
        Retourne le compte par défaut pour une opération
        type_operation: 'vente', 'achat', 'depense', 'tva', 'banque', 'caisse'
        role: 'principal', 'tva', 'client', 'fournisseur', 'banque'
        """
        mapping_defaut = {
            ('vente', 'principal'): '707000',
            ('vente', 'tva'): '445710',
            ('vente', 'client'): '411000',
            ('achat', 'principal'): '607000',
            ('achat', 'tva'): '445660',
            ('achat', 'fournisseur'): '401000',
            ('depense', 'principal'): '606000',
            ('depense', 'tva'): '445660',
            ('paiement', 'banque'): '512000',
            ('paiement', 'caisse'): '530000',
        }
        
        return mapping_defaut.get((type_operation, role))
    
    def exporter_plan_comptable(self, format: str = 'json') -> str:
        """Exporte le plan comptable"""
        comptes = self.rechercher_comptes({'actif': True})
        
        if format == 'json':
            data = [{
                'code': c.code,
                'intitule': c.intitule,
                'classe': c.classe,
                'type': c.type,
                'tiers_lie': c.tiers_lie.value if c.tiers_lie else None,
                'tva_applicable': c.tva_applicable,
                'taux_tva': c.taux_tva
            } for c in comptes]
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif format == 'csv':
            csv_lines = ["code;intitule;classe;type;tiers_lie;tva_applicable;taux_tva"]
            for c in comptes:
                csv_lines.append(f"{c.code};{c.intitule};{c.classe};{c.type};{c.tiers_lie.value if c.tiers_lie else ''};{c.tva_applicable};{c.taux_tva or ''}")
            return "\n".join(csv_lines)
        
        return ""

# =====================================================================
# 3. MOTEUR DE COMPTABILISATION AUTOMATIQUE
# =====================================================================

class MoteurComptabilisation:
    """Génère automatiquement les écritures comptables à partir des opérations commerciales"""
    
    def __init__(self, gestionnaire_plan: GestionnairePlanComptable):
        self.gestionnaire_plan = gestionnaire_plan
        self.regles = []
        self._charger_regles_defaut()
    
    def _charger_regles_defaut(self):
        """Charge les règles de comptabilisation par défaut"""
        self.regles = [
            RegleComptabilisation(
                id="vente_facture",
                module_source="ventes",
                type_operation="facture_client",
                conditions={"type_document": "facture", "statut": "validée"},
                comptes_defaut={
                    "compte_client": "411000",
                    "compte_vente": "707000",
                    "compte_tva": "445710",
                    "compte_port": "708500",
                    "compte_escompte": "709100"
                },
                ordre=10
            ),
            RegleComptabilisation(
                id="achat_facture",
                module_source="achats",
                type_operation="facture_fournisseur",
                conditions={"type_document": "facture", "statut": "à payer"},
                comptes_defaut={
                    "compte_fournisseur": "401000",
                    "compte_achat": "607000",
                    "compte_tva": "445660",
                    "compte_frais": "606000"
                },
                ordre=20
            ),
            RegleComptabilisation(
                id="depense",
                module_source="depenses",
                type_operation="depense_divers",
                conditions={"categorie": ["frais", "achat_immobilisation", "honoraire"]},
                comptes_defaut={
                    "compte_banque": "512000",
                    "compte_caisse": "530000",
                    "compte_charge": "606000",
                    "compte_tva": "445660"
                },
                ordre=30
            ),
            RegleComptabilisation(
                id="paiement_client",
                module_source="ventes",
                type_operation="paiement_client",
                conditions={"mode_paiement": ["virement", "cheque", "carte", "espece"]},
                comptes_defaut={
                    "compte_banque": "512000",
                    "compte_caisse": "530000",
                    "compte_client": "411000"
                },
                ordre=40
            ),
            RegleComptabilisation(
                id="paiement_fournisseur",
                module_source="achats",
                type_operation="paiement_fournisseur",
                conditions={"mode_paiement": ["virement", "cheque", "prelevement"]},
                comptes_defaut={
                    "compte_banque": "512000",
                    "compte_fournisseur": "401000"
                },
                ordre=50
            )
        ]
    
    def get_regle(self, module_source: str, type_operation: str, donnees: Dict) -> Optional[RegleComptabilisation]:
        """Trouve une règle applicable"""
        for regle in sorted(self.regles, key=lambda x: x.ordre):
            if (regle.module_source == module_source and 
                regle.type_operation == type_operation and
                regle.actif and
                self._verifier_conditions(regle.conditions, donnees)):
                return regle
        return None
    
    def _verifier_conditions(self, conditions: Dict, donnees: Dict) -> bool:
        """Vérifie si les conditions sont remplies"""
        for champ, valeur_attendue in conditions.items():
            if champ not in donnees:
                return False
            
            valeur_donnee = donnees[champ]
            
            if isinstance(valeur_attendue, list):
                if valeur_donnee not in valeur_attendue:
                    return False
            elif valeur_donnee != valeur_attendue:
                return False
        
        return True
    
    def generer_ecriture_vente(self, facture: Dict) -> Optional[EcritureComptable]:
        """Génère une écriture pour une vente"""
        regle = self.get_regle("ventes", "facture_client", facture)
        if not regle:
            logger.warning(f"Aucune règle trouvée pour la vente {facture.get('numero')}")
            return None
        
        # Récupérer les comptes (personnalisés ou par défaut)
        compte_client = regle.comptes_personnalises.get('compte_client') or regle.comptes_defaut['compte_client']
        compte_vente = regle.comptes_personnalises.get('compte_vente') or regle.comptes_defaut['compte_vente']
        compte_tva = regle.comptes_personnalises.get('compte_tva') or regle.comptes_defaut['compte_tva']
        
        # Créer l'écriture
        ecriture = EcritureComptable(
            date=date.fromisoformat(facture['date']),
            journal=TypeJournal.VENTES,
            numero_piece=facture.get('numero'),
            libelle=f"Facture client {facture.get('numero')} - {facture.get('client_nom')}",
            module_source="ventes",
            reference_source=facture.get('id')
        )
        
        # Ligne client (débit)
        ecriture.lignes.append(LigneEcriture(
            compte=compte_client,
            libelle=f"Client {facture.get('client_nom')}",
            debit=Decimal(str(facture['total_ttc'])),
            credit=Decimal("0"),
            tiers_id=facture.get('client_id'),
            tiers_type=TypeTiers.CLIENT
        ))
        
        # Ligne vente HT (crédit)
        ecriture.lignes.append(LigneEcriture(
            compte=compte_vente,
            libelle=f"Vente {facture.get('numero')}",
            debit=Decimal("0"),
            credit=Decimal(str(facture['total_ht'])),
            analytique=facture.get('projet_id')
        ))
        
        # Ligne TVA (crédit)
        if facture.get('total_tva', 0) > 0:
            ecriture.lignes.append(LigneEcriture(
                compte=compte_tva,
                libelle=f"TVA {facture.get('numero')}",
                debit=Decimal("0"),
                credit=Decimal(str(facture['total_tva']))
            ))
        
        # Vérifier l'équilibre
        if not self._verifier_equilibre(ecriture):
            logger.error(f"Écriture non équilibrée pour la facture {facture.get('numero')}")
            return None
        
        logger.info(f"Écriture générée pour la vente {facture.get('numero')}")
        return ecriture
    
    def generer_ecriture_achat(self, facture_fournisseur: Dict) -> Optional[EcritureComptable]:
        """Génère une écriture pour un achat"""
        regle = self.get_regle("achats", "facture_fournisseur", facture_fournisseur)
        if not regle:
            logger.warning(f"Aucune règle trouvée pour l'achat {facture_fournisseur.get('numero')}")
            return None
        
        compte_fournisseur = regle.comptes_personnalises.get('compte_fournisseur') or regle.comptes_defaut['compte_fournisseur']
        compte_achat = regle.comptes_personnalises.get('compte_achat') or regle.comptes_defaut['compte_achat']
        compte_tva = regle.comptes_personnalises.get('compte_tva') or regle.comptes_defaut['compte_tva']
        
        ecriture = EcritureComptable(
            date=date.fromisoformat(facture_fournisseur['date']),
            journal=TypeJournal.ACHATS,
            numero_piece=facture_fournisseur.get('numero'),
            libelle=f"Facture fournisseur {facture_fournisseur.get('numero')} - {facture_fournisseur.get('fournisseur_nom')}",
            module_source="achats",
            reference_source=facture_fournisseur.get('id')
        )
        
        # Ligne achat HT (débit)
        ecriture.lignes.append(LigneEcriture(
            compte=compte_achat,
            libelle=f"Achat {facture_fournisseur.get('numero')}",
            debit=Decimal(str(facture_fournisseur['total_ht'])),
            credit=Decimal("0")
        ))
        
        # Ligne TVA (débit)
        if facture_fournisseur.get('total_tva', 0) > 0:
            ecriture.lignes.append(LigneEcriture(
                compte=compte_tva,
                libelle=f"TVA déductible {facture_fournisseur.get('numero')}",
                debit=Decimal(str(facture_fournisseur['total_tva'])),
                credit=Decimal("0")
            ))
        
        # Ligne fournisseur (crédit)
        ecriture.lignes.append(LigneEcriture(
            compte=compte_fournisseur,
            libelle=f"Fournisseur {facture_fournisseur.get('fournisseur_nom')}",
            debit=Decimal("0"),
            credit=Decimal(str(facture_fournisseur['total_ttc'])),
            tiers_id=facture_fournisseur.get('fournisseur_id'),
            tiers_type=TypeTiers.FOURNISSEUR
        ))
        
        if not self._verifier_equilibre(ecriture):
            logger.error(f"Écriture non équilibrée pour l'achat {facture_fournisseur.get('numero')}")
            return None
        
        logger.info(f"Écriture générée pour l'achat {facture_fournisseur.get('numero')}")
        return ecriture
    
    def generer_ecriture_depense(self, depense: Dict) -> Optional[EcritureComptable]:
        """Génère une écriture pour une dépense"""
        regle = self.get_regle("depenses", "depense_divers", depense)
        if not regle:
            logger.warning(f"Aucune règle trouvée pour la dépense {depense.get('id')}")
            return None
        
        compte_charge = regle.comptes_personnalises.get('compte_charge') or regle.comptes_defaut['compte_charge']
        compte_tva = regle.comptes_personnalises.get('compte_tva') or regle.comptes_defaut['compte_tva']
        compte_banque = regle.comptes_personnalises.get('compte_banque') or regle.comptes_defaut['compte_banque']
        compte_caisse = regle.comptes_personnalises.get('compte_caisse') or regle.comptes_defaut['compte_caisse']
        
        ecriture = EcritureComptable(
            date=date.fromisoformat(depense['date']),
            journal=TypeJournal.OPERATIONS_DIVERSES,
            numero_piece=depense.get('numero'),
            libelle=f"Dépense: {depense.get('description')}",
            module_source="depenses",
            reference_source=depense.get('id')
        )
        
        # Déterminer le compte de règlement
        mode_paiement = depense.get('mode_paiement', 'carte')
        compte_reglement = compte_banque if mode_paiement in ['virement', 'carte', 'prelevement'] else compte_caisse
        
        # Ligne charge HT (débit)
        ecriture.lignes.append(LigneEcriture(
            compte=compte_charge,
            libelle=depense.get('description'),
            debit=Decimal(str(depense['montant_ht'])),
            credit=Decimal("0")
        ))
        
        # Ligne TVA (débit)
        if depense.get('montant_tva', 0) > 0:
            ecriture.lignes.append(LigneEcriture(
                compte=compte_tva,
                libelle=f"TVA déductible {depense.get('description')}",
                debit=Decimal(str(depense['montant_tva'])),
                credit=Decimal("0")
            ))
        
        # Ligne banque/caisse (crédit)
        ecriture.lignes.append(LigneEcriture(
            compte=compte_reglement,
            libelle=f"Paiement {depense.get('description')}",
            debit=Decimal("0"),
            credit=Decimal(str(depense.get('montant_ttc', depense['montant_ht'])))
        ))
        
        if not self._verifier_equilibre(ecriture):
            logger.error(f"Écriture non équilibrée pour la dépense {depense.get('id')}")
            return None
        
        logger.info(f"Écriture générée pour la dépense {depense.get('id')}")
        return ecriture
    
    def generer_ecriture_paiement(self, paiement: Dict) -> Optional[EcritureComptable]:
        """Génère une écriture pour un paiement"""
        if paiement.get('type_tiers') == 'client':
            return self._generer_ecriture_paiement_client(paiement)
        elif paiement.get('type_tiers') == 'fournisseur':
            return self._generer_ecriture_paiement_fournisseur(paiement)
        return None
    
    def _generer_ecriture_paiement_client(self, paiement: Dict) -> Optional[EcritureComptable]:
        """Génère une écriture pour un paiement client"""
        regle = self.get_regle("ventes", "paiement_client", paiement)
        if not regle:
            return None
        
        compte_client = regle.comptes_personnalises.get('compte_client') or regle.comptes_defaut['compte_client']
        compte_banque = regle.comptes_personnalises.get('compte_banque') or regle.comptes_defaut['compte_banque']
        compte_caisse = regle.comptes_personnalises.get('compte_caisse') or regle.comptes_defaut['compte_caisse']
        
        mode_paiement = paiement.get('mode_paiement', 'virement')
        compte_reglement = compte_banque if mode_paiement in ['virement', 'cheque', 'carte'] else compte_caisse
        
        ecriture = EcritureComptable(
            date=date.fromisoformat(paiement['date']),
            journal=TypeJournal.BANQUE if mode_paiement != 'espece' else TypeJournal.CAISSE,
            numero_piece=paiement.get('numero'),
            libelle=f"Paiement client {paiement.get('client_nom')}",
            module_source="ventes",
            reference_source=paiement.get('id')
        )
        
        # Ligne banque/caisse (débit)
        ecriture.lignes.append(LigneEcriture(
            compte=compte_reglement,
            libelle=f"Paiement {paiement.get('client_nom')}",
            debit=Decimal(str(paiement['montant'])),
            credit=Decimal("0")
        ))
        
        # Ligne client (crédit)
        ecriture.lignes.append(LigneEcriture(
            compte=compte_client,
            libelle=f"Règlement client {paiement.get('client_nom')}",
            debit=Decimal("0"),
            credit=Decimal(str(paiement['montant'])),
            tiers_id=paiement.get('client_id'),
            tiers_type=TypeTiers.CLIENT
        ))
        
        if not self._verifier_equilibre(ecriture):
            return None
        
        return ecriture
    
    def _generer_ecriture_paiement_fournisseur(self, paiement: Dict) -> Optional[EcritureComptable]:
        """Génère une écriture pour un paiement fournisseur"""
        regle = self.get_regle("achats", "paiement_fournisseur", paiement)
        if not regle:
            return None
        
        compte_fournisseur = regle.comptes_personnalises.get('compte_fournisseur') or regle.comptes_defaut['compte_fournisseur']
        compte_banque = regle.comptes_personnalises.get('compte_banque') or regle.comptes_defaut['compte_banque']
        
        ecriture = EcritureComptable(
            date=date.fromisoformat(paiement['date']),
            journal=TypeJournal.BANQUE,
            numero_piece=paiement.get('numero'),
            libelle=f"Paiement fournisseur {paiement.get('fournisseur_nom')}",
            module_source="achats",
            reference_source=paiement.get('id')
        )
        
        # Ligne fournisseur (débit)
        ecriture.lignes.append(LigneEcriture(
            compte=compte_fournisseur,
            libelle=f"Paiement {paiement.get('fournisseur_nom')}",
            debit=Decimal(str(paiement['montant'])),
            credit=Decimal("0"),
            tiers_id=paiement.get('fournisseur_id'),
            tiers_type=TypeTiers.FOURNISSEUR
        ))
        
        # Ligne banque (crédit)
        ecriture.lignes.append(LigneEcriture(
            compte=compte_banque,
            libelle=f"Virement {paiement.get('fournisseur_nom')}",
            debit=Decimal("0"),
            credit=Decimal(str(paiement['montant']))
        ))
        
        if not self._verifier_equilibre(ecriture):
            return None
        
        return ecriture
    
    def _verifier_equilibre(self, ecriture: EcritureComptable) -> bool:
        """Vérifie qu'une écriture est équilibrée"""
        total_debit = sum(ligne.debit for ligne in ecriture.lignes)
        total_credit = sum(ligne.credit for ligne in ecriture.lignes)
        return total_debit == total_credit
    
    def personnaliser_regle(self, regle_id: str, comptes_personnalises: Dict[str, str]) -> bool:
        """Personnalise les comptes d'une règle"""
        for regle in self.regles:
            if regle.id == regle_id:
                regle.comptes_personnalises.update(comptes_personnalises)
                logger.info(f"Règle {regle_id} personnalisée")
                return True
        return False

# =====================================================================
# 4. GESTIONNAIRE D'ÉCRITURES COMPTABLES
# =====================================================================

class GestionnaireEcritures:
    """Gère le stockage et la récupération des écritures comptables"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or ":memory:"
        self._init_db()
    
    def _init_db(self):
        """Initialise la base de données pour les écritures"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        # Table principale des écritures
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ecritures (
                id TEXT PRIMARY KEY,
                date DATE NOT NULL,
                journal TEXT NOT NULL,
                numero_piece TEXT,
                libelle TEXT NOT NULL,
                lettree BOOLEAN DEFAULT 0,
                rapprochee BOOLEAN DEFAULT 0,
                module_source TEXT,
                reference_source TEXT,
                validee BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table des lignes d'écriture
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lignes_ecritures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ecriture_id TEXT NOT NULL,
                compte TEXT NOT NULL,
                libelle TEXT NOT NULL,
                debit DECIMAL(15,2) DEFAULT 0,
                credit DECIMAL(15,2) DEFAULT 0,
                tiers_id TEXT,
                tiers_type TEXT,
                analytique TEXT,
                quantite DECIMAL(15,3),
                FOREIGN KEY (ecriture_id) REFERENCES ecritures(id) ON DELETE CASCADE
            )
        ''')
        
        # Index pour les performances
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ecritures_date ON ecritures(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ecritures_journal ON ecritures(journal)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ecritures_source ON ecritures(module_source, reference_source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lignes_compte ON lignes_ecritures(compte)')
        
        self.conn.commit()
    
    def sauvegarder_ecriture(self, ecriture: EcritureComptable) -> str:
        """Sauvegarde une écriture dans la base de données"""
        try:
            cursor = self.conn.cursor()
            
            # Générer un ID si nécessaire
            if not ecriture.id:
                import uuid
                ecriture.id = str(uuid.uuid4())[:8]
            
            # Insérer l'écriture principale
            cursor.execute('''
                INSERT OR REPLACE INTO ecritures 
                (id, date, journal, numero_piece, libelle, lettree, rapprochee, module_source, reference_source, validee)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ecriture.id,
                ecriture.date.isoformat(),
                ecriture.journal.value,
                ecriture.numero_piece,
                ecriture.libelle,
                1 if ecriture.lettree else 0,
                1 if ecriture.rapprochee else 0,
                ecriture.module_source,
                ecriture.reference_source,
                1 if ecriture.validee else 0
            ))
            
            # Supprimer les anciennes lignes
            cursor.execute('DELETE FROM lignes_ecritures WHERE ecriture_id = ?', (ecriture.id,))
            
            # Insérer les nouvelles lignes
            for ligne in ecriture.lignes:
                cursor.execute('''
                    INSERT INTO lignes_ecritures 
                    (ecriture_id, compte, libelle, debit, credit, tiers_id, tiers_type, analytique, quantite)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ecriture.id,
                    ligne.compte,
                    ligne.libelle,
                    float(ligne.debit),
                    float(ligne.credit),
                    ligne.tiers_id,
                    ligne.tiers_type.value if ligne.tiers_type else None,
                    ligne.analytique,
                    float(ligne.quantite) if ligne.quantite else None
                ))
            
            self.conn.commit()
            logger.info(f"Écriture {ecriture.id} sauvegardée")
            return ecriture.id
        
        except Exception as e:
            logger.error(f"Erreur sauvegarde écriture: {e}")
            self.conn.rollback()
            raise
    
    def get_ecriture(self, ecriture_id: str) -> Optional[EcritureComptable]:
        """Récupère une écriture par son ID"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM ecritures WHERE id = ?', (ecriture_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        # Récupérer les lignes
        cursor.execute('SELECT * FROM lignes_ecritures WHERE ecriture_id = ?', (ecriture_id,))
        lignes_rows = cursor.fetchall()
        
        # Construire l'objet EcritureComptable
        ecriture = EcritureComptable(
            id=row['id'],
            date=date.fromisoformat(row['date']),
            journal=TypeJournal(row['journal']),
            numero_piece=row['numero_piece'],
            libelle=row['libelle'],
            lettree=bool(row['lettree']),
            rapprochee=bool(row['rapprochee']),
            module_source=row['module_source'],
            reference_source=row['reference_source'],
            validee=bool(row['validee']),
            created_at=datetime.datetime.fromisoformat(row['created_at'])
        )
        
        # Ajouter les lignes
        for ligne_row in lignes_rows:
            ligne = LigneEcriture(
                compte=ligne_row['compte'],
                libelle=ligne_row['libelle'],
                debit=Decimal(str(ligne_row['debit'])),
                credit=Decimal(str(ligne_row['credit'])),
                tiers_id=ligne_row['tiers_id'],
                tiers_type=TypeTiers(ligne_row['tiers_type']) if ligne_row['tiers_type'] else None,
                analytique=ligne_row['analytique'],
                quantite=Decimal(str(ligne_row['quantite'])) if ligne_row['quantite'] else None
            )
            ecriture.lignes.append(ligne)
        
        return ecriture
    
    def rechercher_ecritures(self, filtre: Dict = None) -> List[EcritureComptable]:
        """Recherche des écritures selon des critères"""
        query = "SELECT id FROM ecritures WHERE 1=1"
        params = []
        
        if filtre:
            if 'date_debut' in filtre:
                query += " AND date >= ?"
                params.append(filtre['date_debut'].isoformat())
            if 'date_fin' in filtre:
                query += " AND date <= ?"
                params.append(filtre['date_fin'].isoformat())
            if 'journal' in filtre:
                query += " AND journal = ?"
                params.append(filtre['journal'].value)
            if 'module_source' in filtre:
                query += " AND module_source = ?"
                params.append(filtre['module_source'])
            if 'reference_source' in filtre:
                query += " AND reference_source = ?"
                params.append(filtre['reference_source'])
            if 'validee' in filtre:
                query += " AND validee = ?"
                params.append(1 if filtre['validee'] else 0)
        
        query += " ORDER BY date, created_at"
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        
        ecritures = []
        for row in cursor.fetchall():
            ecriture = self.get_ecriture(row['id'])
            if ecriture:
                ecritures.append(ecriture)
        
        return ecritures
    
    def generer_balance(self, date_debut: date, date_fin: date) -> Dict:
        """Génère une balance des comptes sur une période"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                l.compte,
                SUM(l.debit) as total_debit,
                SUM(l.credit) as total_credit
            FROM lignes_ecritures l
            JOIN ecritures e ON l.ecriture_id = e.id
            WHERE e.date BETWEEN ? AND ?
                AND e.validee = 1
            GROUP BY l.compte
            ORDER BY l.compte
        ''', (date_debut.isoformat(), date_fin.isoformat()))
        
        balance = {}
        for row in cursor.fetchall():
            solde = Decimal(str(row['total_debit'])) - Decimal(str(row['total_credit']))
            balance[row['compte']] = {
                'debit': float(row['total_debit']),
                'credit': float(row['total_credit']),
                'solde_debiteur': float(solde) if solde > 0 else 0,
                'solde_crediteur': float(-solde) if solde < 0 else 0
            }
        
        return balance
    
    def get_statistiques(self) -> Dict:
        """Retourne des statistiques sur les écritures"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Nombre total d'écritures
        cursor.execute('SELECT COUNT(*) as total FROM ecritures')
        stats['total_ecritures'] = cursor.fetchone()['total']
        
        # Nombre par journal
        cursor.execute('SELECT journal, COUNT(*) as count FROM ecritures GROUP BY journal')
        stats['par_journal'] = {row['journal']: row['count'] for row in cursor.fetchall()}
        
        # Nombre par mois (derniers 12 mois)
        cursor.execute('''
            SELECT 
                strftime('%Y-%m', date) as mois,
                COUNT(*) as count
            FROM ecritures
            WHERE date >= date('now', '-12 months')
            GROUP BY mois
            ORDER BY mois
        ''')
        stats['par_mois'] = {row['mois']: row['count'] for row in cursor.fetchall()}
        
        return stats

# =====================================================================
# 5. INTÉGRATION AVEC LES MODULES COMMERCIAUX
# =====================================================================

class IntegrateurCommercialComptable:
    """Intègre la comptabilité avec les modules commerciaux existants"""
    
    def __init__(self, moteur: MoteurComptabilisation, gestionnaire_ecritures: GestionnaireEcritures):
        self.moteur = moteur
        self.gestionnaire_ecritures = gestionnaire_ecritures
        self.hooks = {}
    
    def enregistrer_hook(self, module: str, callback):
        """Enregistre un hook pour être notifié des écritures générées"""
        if module not in self.hooks:
            self.hooks[module] = []
        self.hooks[module].append(callback)
    
    def _notifier_hooks(self, module: str, ecriture: EcritureComptable):
        """Notifie les hooks enregistrés"""
        if module in self.hooks:
            for callback in self.hooks[module]:
                try:
                    callback(ecriture)
                except Exception as e:
                    logger.error(f"Erreur dans le hook {callback.__name__}: {e}")
    
    def traiter_facture_vente(self, facture: Dict) -> Optional[str]:
        """Traite une facture de vente et génère l'écriture correspondante"""
        try:
            ecriture = self.moteur.generer_ecriture_vente(facture)
            if ecriture:
                ecriture_id = self.gestionnaire_ecritures.sauvegarder_ecriture(ecriture)
                self._notifier_hooks('ventes', ecriture)
                
                # Mettre à jour la facture avec la référence de l'écriture
                if 'metadata' not in facture:
                    facture['metadata'] = {}
                facture['metadata']['ecriture_comptable_id'] = ecriture_id
                facture['metadata']['comptabilisee'] = True
                
                logger.info(f"Facture vente {facture.get('numero')} comptabilisée")
                return ecriture_id
        except Exception as e:
            logger.error(f"Erreur traitement facture vente: {e}")
        return None
    
    def traiter_facture_achat(self, facture: Dict) -> Optional[str]:
        """Traite une facture d'achat et génère l'écriture correspondante"""
        try:
            ecriture = self.moteur.generer_ecriture_achat(facture)
            if ecriture:
                ecriture_id = self.gestionnaire_ecritures.sauvegarder_ecriture(ecriture)
                self._notifier_hooks('achats', ecriture)
                
                if 'metadata' not in facture:
                    facture['metadata'] = {}
                facture['metadata']['ecriture_comptable_id'] = ecriture_id
                facture['metadata']['comptabilisee'] = True
                
                logger.info(f"Facture achat {facture.get('numero')} comptabilisée")
                return ecriture_id
        except Exception as e:
            logger.error(f"Erreur traitement facture achat: {e}")
        return None
    
    def traiter_depense(self, depense: Dict) -> Optional[str]:
        """Traite une dépense et génère l'écriture correspondante"""
        try:
            ecriture = self.moteur.generer_ecriture_depense(depense)
            if ecriture:
                ecriture_id = self.gestionnaire_ecritures.sauvegarder_ecriture(ecriture)
                self._notifier_hooks('depenses', ecriture)
                
                if 'metadata' not in depense:
                    depense['metadata'] = {}
                depense['metadata']['ecriture_comptable_id'] = ecriture_id
                depense['metadata']['comptabilisee'] = True
                
                logger.info(f"Dépense {depense.get('id')} comptabilisée")
                return ecriture_id
        except Exception as e:
            logger.error(f"Erreur traitement dépense: {e}")
        return None
    
    def traiter_paiement(self, paiement: Dict) -> Optional[str]:
        """Traite un paiement et génère l'écriture correspondante"""
        try:
            ecriture = self.moteur.generer_ecriture_paiement(paiement)
            if ecriture:
                ecriture_id = self.gestionnaire_ecritures.sauvegarder_ecriture(ecriture)
                module = 'ventes' if paiement.get('type_tiers') == 'client' else 'achats'
                self._notifier_hooks(module, ecriture)
                
                if 'metadata' not in paiement:
                    paiement['metadata'] = {}
                paiement['metadata']['ecriture_comptable_id'] = ecriture_id
                paiement['metadata']['comptabilisee'] = True
                
                logger.info(f"Paiement {paiement.get('id')} comptabilisé")
                return ecriture_id
        except Exception as e:
            logger.error(f"Erreur traitement paiement: {e}")
        return None
    
    def annuler_ecriture(self, reference_source: str, module_source: str) -> bool:
        """Annule une écriture (crée une écriture inverse)"""
        try:
            # Récupérer l'écriture originale
            filtre = {
                'reference_source': reference_source,
                'module_source': module_source
            }
            ecritures = self.gestionnaire_ecritures.rechercher_ecritures(filtre)
            
            if not ecritures:
                logger.warning(f"Aucune écriture trouvée pour {reference_source}")
                return False
            
            ecriture_originale = ecritures[0]
            
            # Créer l'écriture d'annulation (inverse)
            ecriture_annulation = EcritureComptable(
                date=date.today(),
                journal=ecriture_originale.journal,
                numero_piece=f"ANNU-{ecriture_originale.numero_piece}",
                libelle=f"Annulation: {ecriture_originale.libelle}",
                module_source=module_source,
                reference_source=f"ANNU-{reference_source}"
            )
            
            # Inverser les lignes
            for ligne in ecriture_originale.lignes:
                ligne_annulation = LigneEcriture(
                    compte=ligne.compte,
                    libelle=f"Annulation: {ligne.libelle}",
                    debit=ligne.credit,  # Inverse
                    credit=ligne.debit,   # Inverse
                    tiers_id=ligne.tiers_id,
                    tiers_type=ligne.tiers_type,
                    analytique=ligne.analytique
                )
                ecriture_annulation.lignes.append(ligne_annulation)
            
            # Sauvegarder l'annulation
            self.gestionnaire_ecritures.sauvegarder_ecriture(ecriture_annulation)
            
            # Marquer l'originale comme annulée
            self._mettre_a_jour_statut_ecriture(ecriture_originale.id, validee=False)
            
            logger.info(f"Écriture {ecriture_originale.id} annulée")
            return True
            
        except Exception as e:
            logger.error(f"Erreur annulation écriture: {e}")
            return False
    
    def _mettre_a_jour_statut_ecriture(self, ecriture_id: str, **kwargs):
        """Met à jour le statut d'une écriture"""
        try:
            cursor = self.gestionnaire_ecritures.conn.cursor()
            
            if 'validee' in kwargs:
                cursor.execute(
                    "UPDATE ecritures SET validee = ? WHERE id = ?",
                    (1 if kwargs['validee'] else 0, ecriture_id)
                )
            
            self.gestionnaire_ecritures.conn.commit()
        except Exception as e:
            logger.error(f"Erreur mise à jour statut écriture: {e}")

# =====================================================================
# 6. INTERFACE UTILISATEUR ET API
# =====================================================================

class APIGestionComptable:
    """API pour intégrer la comptabilité dans votre interface"""
    
    def __init__(self, db_path: str = "gestion_commerciale.db"):
        self.gestionnaire_plan = GestionnairePlanComptable(f"{db_path}.plan_comptable")
        self.gestionnaire_ecritures = GestionnaireEcritures(f"{db_path}.ecritures")
        self.moteur = MoteurComptabilisation(self.gestionnaire_plan)
        self.integrateur = IntegrateurCommercialComptable(self.moteur, self.gestionnaire_ecritures)
    
    # === GESTION DU PLAN COMPTABLE ===
    
    def get_comptes(self, filtre: Dict = None) -> List[Dict]:
        """Récupère la liste des comptes"""
        comptes = self.gestionnaire_plan.rechercher_comptes(filtre)
        return [self._compte_to_dict(c) for c in comptes]
    
    def ajouter_compte(self, compte_data: Dict) -> Dict:
        """Ajoute un nouveau compte"""
        compte = CompteComptable(
            code=compte_data['code'],
            intitule=compte_data['intitule'],
            classe=compte_data['classe'],
            type=compte_data['type'],
            tiers_lie=TypeTiers(compte_data['tiers_lie']) if compte_data.get('tiers_lie') else None,
            tva_applicable=compte_data.get('tva_applicable', False),
            taux_tva=compte_data.get('taux_tva'),
            metadata=compte_data.get('metadata', {})
        )
        
        succes = self.gestionnaire_plan.ajouter_compte(compte)
        return {'success': succes, 'compte': self._compte_to_dict(compte) if succes else None}
    
    def personnaliser_compte_operation(self, type_operation: str, role: str, nouveau_compte: str) -> bool:
        """Personnalise le compte utilisé pour une opération spécifique"""
        # Trouver la règle correspondante
        regle_id = None
        for regle in self.moteur.regles:
            if (regle.type_operation.startswith(type_operation) or 
                type_operation in regle.type_operation):
                regle_id = regle.id
                break
        
        if regle_id:
            mapping = {f"compte_{role}": nouveau_compte}
            return self.moteur.personnaliser_regle(regle_id, mapping)
        
        return False
    
    # === GESTION DES ÉCRITURES ===
    
    def comptabiliser_facture_vente(self, facture_data: Dict) -> Dict:
        """Comptabilise une facture de vente"""
        ecriture_id = self.integrateur.traiter_facture_vente(facture_data)
        return {
            'success': ecriture_id is not None,
            'ecriture_id': ecriture_id,
            'facture': facture_data
        }
    
    def comptabiliser_facture_achat(self, facture_data: Dict) -> Dict:
        """Comptabilise une facture d'achat"""
        ecriture_id = self.integrateur.traiter_facture_achat(facture_data)
        return {
            'success': ecriture_id is not None,
            'ecriture_id': ecriture_id,
            'facture': facture_data
        }
    
    def comptabiliser_depense(self, depense_data: Dict) -> Dict:
        """Comptabilise une dépense"""
        ecriture_id = self.integrateur.traiter_depense(depense_data)
        return {
            'success': ecriture_id is not None,
            'ecriture_id': ecriture_id,
            'depense': depense_data
        }
    
    def get_ecritures(self, filtre: Dict = None) -> List[Dict]:
        """Récupère les écritures"""
        ecritures = self.gestionnaire_ecritures.rechercher_ecritures(filtre)
        return [self._ecriture_to_dict(e) for e in ecritures]
    
    def get_balance(self, date_debut: str, date_fin: str) -> Dict:
        """Génère la balance comptable"""
        date_debut_obj = date.fromisoformat(date_debut)
        date_fin_obj = date.fromisoformat(date_fin)
        
        balance = self.gestionnaire_ecritures.generer_balance(date_debut_obj, date_fin_obj)
        
        # Enrichir avec les intitulés des comptes
        balance_enrichie = {}
        for compte_code, donnees in balance.items():
            compte = self.gestionnaire_plan.comptes.get(compte_code, None)
            intitule = compte.intitule if compte else "Compte inconnu"
            
            balance_enrichie[compte_code] = {
                'intitule': intitule,
                **donnees
            }
        
        # Calculer les totaux
        total_debit = sum(d['debit'] for d in balance_enrichie.values())
        total_credit = sum(d['credit'] for d in balance_enrichie.values())
        
        return {
            'periode': f"{date_debut} - {date_fin}",
            'balance': balance_enrichie,
            'totaux': {
                'debit': total_debit,
                'credit': total_credit,
                'difference': total_debit - total_credit
            }
        }
    
    # === RAPPORTS ===
    
    def get_rapport_tva(self, trimestre: int, annee: int) -> Dict:
        """Génère un rapport de TVA pour un trimestre"""
        # Calculer les dates du trimestre
        if trimestre == 1:
            date_debut = date(annee, 1, 1)
            date_fin = date(annee, 3, 31)
        elif trimestre == 2:
            date_debut = date(annee, 4, 1)
            date_fin = date(annee, 6, 30)
        elif trimestre == 3:
            date_debut = date(annee, 7, 1)
            date_fin = date(annee, 9, 30)
        else:
            date_debut = date(annee, 10, 1)
            date_fin = date(annee, 12, 31)
        
        balance = self.gestionnaire_ecritures.generer_balance(date_debut, date_fin)
        
        # Filtrer les comptes de TVA
        tva_collectee = Decimal('0')
        tva_deductible = Decimal('0')
        
        for compte_code, donnees in balance.items():
            if compte_code.startswith('44571'):  # TVA collectée
                tva_collectee += Decimal(str(donnees['credit'])) - Decimal(str(donnees['debit']))
            elif compte_code.startswith('44566'):  # TVA déductible
                tva_deductible += Decimal(str(donnees['debit'])) - Decimal(str(donnees['credit']))
        
        tva_a_payer = tva_collectee - tva_deductible
        
        return {
            'trimestre': trimestre,
            'annee': annee,
            'tva_collectee': float(tva_collectee),
            'tva_deductible': float(tva_deductible),
            'tva_a_payer': float(tva_a_payer),
            'credit_tva': float(-tva_a_payer) if tva_a_payer < 0 else 0
        }
    
    # === UTILITAIRES ===
    
    def _compte_to_dict(self, compte: CompteComptable) -> Dict:
        """Convertit un objet CompteComptable en dictionnaire"""
        return {
            'code': compte.code,
            'intitule': compte.intitule,
            'classe': compte.classe,
            'type': compte.type,
            'tiers_lie': compte.tiers_lie.value if compte.tiers_lie else None,
            'tva_applicable': compte.tva_applicable,
            'taux_tva': compte.taux_tva,
            'actif': compte.actif,
            'metadata': compte.metadata
        }
    
    def _ecriture_to_dict(self, ecriture: EcritureComptable) -> Dict:
        """Convertit un objet EcritureComptable en dictionnaire"""
        return {
            'id': ecriture.id,
            'date': ecriture.date.isoformat(),
            'journal': ecriture.journal.value,
            'numero_piece': ecriture.numero_piece,
            'libelle': ecriture.libelle,
            'lignes': [{
                'compte': ligne.compte,
                'libelle': ligne.libelle,
                'debit': float(ligne.debit),
                'credit': float(ligne.credit),
                'tiers_id': ligne.tiers_id,
                'tiers_type': ligne.tiers_type.value if ligne.tiers_type else None,
                'analytique': ligne.analytique
            } for ligne in ecriture.lignes],
            'module_source': ecriture.module_source,
            'reference_source': ecriture.reference_source,
            'validee': ecriture.validee
        }

# =====================================================================
# EXPORT FEC
# =====================================================================

class ExportFEC:
    """Exporte les écritures au format FEC (Fichier des Écritures Comptables)"""
    
    @staticmethod
    def generer_fec(api_comptable, date_debut: date, date_fin: date, fichier_sortie: str):
        """Génère un fichier FEC"""
        import csv
        
        # Récupérer les écritures
        ecritures = api_comptable.get_ecritures({
            'date_debut': date_debut,
            'date_fin': date_fin,
            'validee': True
        })
        
        lignes_fec = []
        
        for ecriture in ecritures:
            ecriture_date = date.fromisoformat(ecriture['date'])
            
            for ligne in ecriture['lignes']:
                ligne_fec = {
                    "JournalCode": ecriture['journal'][:3],
                    "JournalLib": ecriture['journal'],
                    "EcritureNum": ecriture['numero_piece'] or ecriture['id'],
                    "EcritureDate": ecriture_date.strftime("%Y%m%d"),
                    "CompteNum": ligne['compte'],
                    "CompteLib": "",  # À remplir avec l'intitulé du compte
                    "CompAuxNum": ligne['tiers_id'] or "",
                    "CompAuxLib": "",  # À remplir avec le nom du tiers
                    "PieceRef": ecriture['numero_piece'] or ecriture['id'],
                    "PieceDate": ecriture_date.strftime("%Y%m%d"),
                    "EcritureLib": ecriture['libelle'],
                    "Debit": f"{ligne['debit']:.2f}".replace('.', ','),
                    "Credit": f"{ligne['credit']:.2f}".replace('.', ','),
                    "EcritureLet": "",
                    "DateLet": "",
                    "ValidDate": ecriture_date.strftime("%Y%m%d"),
                    "Montantdevise": "",
                    "Idevise": ""
                }
                lignes_fec.append(ligne_fec)
        
        # Enrichir avec les intitulés
        comptes = api_comptable.get_comptes()
        comptes_dict = {c['code']: c['intitule'] for c in comptes}
        
        for ligne in lignes_fec:
            ligne['CompteLib'] = comptes_dict.get(ligne['CompteNum'], "")
        
        # Écrire le fichier CSV
        with open(fichier_sortie, 'w', newline='', encoding='utf-8') as f:
            if lignes_fec:
                writer = csv.DictWriter(f, fieldnames=lignes_fec[0].keys(), delimiter='\t')
                writer.writeheader()
                writer.writerows(lignes_fec)
        
        return len(lignes_fec)

# =====================================================================
# POINT D'ENTRÉE POUR LES TESTS
# =====================================================================

if __name__ == "__main__":
    print("Module d'intégration comptable - Test")
    print("="*60)
    
    # Créer une instance
    api = APIGestionComptable("test.db")
    
    print("✓ Module initialisé avec succès")
    print(f"✓ {len(api.get_comptes())} comptes dans le plan comptable")
    
    # Test de création d'une facture
    facture_test = {
        'id': 'TEST-001',
        'numero': 'F2024-TEST-001',
        'date': date.today().isoformat(),
        'client_id': 'CL-TEST',
        'client_nom': 'Client Test',
        'total_ht': 1000.00,
        'total_tva': 200.00,
        'total_ttc': 1200.00,
        'statut': 'validée',
        'type_document': 'facture'
    }
    
    result = api.comptabiliser_facture_vente(facture_test)
    print(f"✓ Facture test comptabilisée: {result['success']}")
    
    # Afficher la balance
    balance = api.get_balance(
        date.today().replace(day=1).isoformat(),
        date.today().isoformat()
    )
    print(f"✓ Balance générée: {len(balance['balance'])} comptes")
    
    print("\nModule prêt à être intégré dans votre logiciel!")