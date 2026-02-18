# vente/domain/calcul_vente.py

class CalculVente:

    @staticmethod
    def calcul_ttc(ht: float, tva: float) -> float:
        return round(ht * (1 + tva / 100), 2)

    @staticmethod
    def calcul_reste(net: float, verse: float) -> float:
        return round(max(net - verse, 0), 2)

    @staticmethod
    def statut(net: float, verse: float) -> str:
        reste = round((net - verse), 2)

        if reste == 0:
            return "Payé"
        elif 0 < verse < net:
            return "Avance"
        elif verse == 0:
            return "Impayé"
        else:
            return "Payé"
