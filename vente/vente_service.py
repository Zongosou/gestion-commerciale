# vente_service.py
from datetime import datetime
class VenteService:
    FACTURE = "Facture"
    FACTUR_VALIDE = "Validée"

    @staticmethod
    def calcul_ttc(ht, tva):
        return round(ht * (1 + tva / 100), 2)

    @staticmethod
    def calcul_reste(net, verse):
        return round(max(net - verse, 0), 2)

    
    @staticmethod
    def statut_paiement(type_piece: str, statut_piece: str, net: float, verse: float):

        # 1️⃣ si type de pièce = facture → vérifier statut
        if type_piece == "Facture":
            if statut_piece == VenteService.FACTUR_VALIDE:
                # 2 Si facture validée → calcul paiement
                reste = round((net - verse), 2)
                if reste <= 0:
                    return "PAYEE"
                elif 0 < verse < net:
                    return "PARTIELLE"
                elif verse == 0:
                    return "IMPAYEE"
                else:
                    return "PAYEE"
            else:
                return "N/A"
        else:
            return "N/A"
