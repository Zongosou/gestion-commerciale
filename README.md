# GsCom - Mini gestion commerciale

Application desktop (PySide6) de gestion commerciale pour petit magasin: stock, ventes, paiements, avoirs, caisse/tresorerie et tableaux de bord.

## Prerequis

- Python 3.11+
- Windows (recommande pour ce depot)
- SQLite (integre a Python)

## Installation

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Lancement

```bash
python main_app.py
```

## Base de donnees

- Base principale attendue: `data/stock.db`
- Le projet lit/cree aussi d'autres fichiers SQLite selon les modules (ex: comptabilite, inventaire).

Conseil: conserver une copie de sauvegarde de `data/stock.db` avant les tests fonctionnels.

## Structure rapide

- `main_app.py`: point d'entree GUI
- `stock/`: gestion articles, mouvements, inventaire
- `vente/`: creation des pieces commerciales
- `piece/`: liste des pieces, paiements, avoirs
- `caisse/`: tresorerie + dashboard
- `compta/`: integration comptable
- `fonction/`: utilitaires communs (DB, modeles PDF, parametrage)
- `template/`: modeles HTML/PDF
- `config/`: style et configuration

## Depannage

- Erreur `database is locked`:
  - fermer les autres instances de l'application,
  - verifier qu'aucun outil externe n'ouvre `data/stock.db`,
  - relancer l'application.

- Erreur de locale `fr_FR.UTF-8` (Windows):
  - adapter le fallback locale dans `fonction/model.py` si necessaire.

- Erreur de dependance:
  - reinstaller: `pip install -r requirements.txt --upgrade`.

## Etat du projet

Le projet est fonctionnel mais en cours de stabilisation. La prochaine etape recommandee est l'ajout de tests automatises sur les flux critiques (vente, paiement, avoir, stock).
