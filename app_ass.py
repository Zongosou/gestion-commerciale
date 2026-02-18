def statut(type_piece: str, statut_piece: str, net: float, verse: float):

    # 1️⃣ si type de pièce = facture → vérifier statut
    if type_piece == "Facture":
        if statut_piece == "Validée":
            # 2 Si facture validée → calcul paiement
            reste = round((net - verse), 2)
            if reste <= 0:
                return "Payé"
            elif 0 < verse < net:
                return "Avance"
            elif verse == 0:
                return "Impayé"
            else:
                return "Payé"
        else:
            return "N/A"
    else:
        return "N/A"

print(statut("Facture", "Validée", 100.0, 50.0))  # Avance
print(statut("Facture", "Validée", 100.0, 100.0)) # Payé
print(statut("Facture", "Validée", 100.0, 0.0))   # Impayé
print(statut("Facture", "Brouillon", 100.0, 50.0)) # N/A
print(statut("Devis", "Validée", 100.0, 50.0)) # N/A