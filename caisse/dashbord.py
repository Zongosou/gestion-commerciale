from PySide6.QtWidgets import ( QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSizePolicy,QGroupBox,QProgressBar,QWidget
)
from PySide6.QtCharts import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon,QPainter,QFont
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from fonction.methode import cal
from stock.gest_stock import SummaryCard


# ----------- Main Dashboard -----------
class Dashboard(QWidget):
    def __init__(self, factures_df, ventes_df,db):
        super().__init__()
        self.setWindowTitle("Tableau de Bord")
        self.setWindowIcon(QIcon(':/icon/314.png'))
        self.db = db
        self.ca_total = 0
        self.montant_paye = 0
        self.montant_impaye = 0
        # === 1. Calcul des indicateurs ===
        self.cal = cal()
        charge_devise = self.cal.charger_tva_devise(self.db)
        # Configuration par défaut si non trouvée
        self.devise = charge_devise["devise"] if charge_devise else "CFA"

        self.dashboard_cards = self.create_dashboard_cards()
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.dashboard_cards)
        
        # Créer une disposition horizontale pour les deux derniers graphiques
        bottom_graphs_layout = QHBoxLayout()

        # bottom_graphs_layout.addWidget(canvas3)
        main_layout.addWidget(self.create_monthly_summary(factures_df))
        # ===  Top 5 Clients ===
        bottom_graphs_layout.addWidget(self.create_top5_clients_chart(ventes_df), 1)
        bottom_graphs_layout.addWidget(self.create_top5_produits_chart(ventes_df), 1)
        # Ajouter le layout horizontal à la disposition principale
        main_layout.addLayout(bottom_graphs_layout)
        self.setLayout(main_layout)
        self.update_data(factures_df)
        # Graphique ventes mensuelles
        
        

            
    def create_top5_produits_chart(self, ventes_df):
        """Crée un QChart pour Top 5 Produits"""
        try:
            top_produits = ventes_df.groupby("libelle")["montant"].sum().nlargest(5)

            set0 = QBarSet("Produits")
            set0.append(top_produits.values.tolist())

            series = QBarSeries()
            series.append(set0)

            chart = QChart()
            chart.addSeries(series)
            chart.setTitle("Top 5 Produits les plus vendus (CA)")
            chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            axisX = QBarCategoryAxis()
            axisX.append(top_produits.index.tolist())
            chart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
            series.attachAxis(axisX)

            chart.legend().setVisible(False)
            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        except Exception as e:
            print(f"Erreur lors de la création du graphique Top 5 Produits: {e}")
            chart_view = QLabel("Aucune donnée disponible pour les produits.")
            chart_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return chart_view

    def create_top5_clients_chart(self, ventes_df):
        """Crée un QChart pour Top 5 Clients"""
        try:
            top_clients = ventes_df.groupby("client")["montant"].sum().nlargest(5)

            set0 = QBarSet("Clients")
            set0.append(top_clients.values.tolist())

            series = QBarSeries()
            series.append(set0)

            chart = QChart()
            chart.addSeries(series)
            chart.setTitle("Top 5 Clients (CA)")
            chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

            axisX = QBarCategoryAxis()
            axisX.append(top_clients.index.tolist())
            chart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
            series.attachAxis(axisX)

            # chart.axisY().setTitleText(f"Montant {self.devise}")

            chart.legend().setVisible(False)
            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        except Exception as e:
            print(f"Erreur lors de la création du graphique Top 5 Clients: {e}")
            chart_view = QLabel("Aucune donnée disponible pour les clients.")
            chart_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return chart_view

            
    def create_dashboard_cards(self):
        widget = QWidget()
        # ================= CARTES =================
        cards_row = QHBoxLayout(widget)
        self.card_total = SummaryCard("Revenu Total", "0.0", accent="#2D7EF7")
        self.card_alerts = SummaryCard("Montant Payé", "0.0", accent="#F59E0B")
        self.card_value = SummaryCard("Montant Restant", "0.0", accent="#10B981")
        for card in (self.card_total, self.card_alerts, self.card_value):
            cards_row.addWidget(card, 1)
        # layout.addLayout(cards_row)
        return widget

    def create_monthly_summary(self, factures_df):
        group = QGroupBox("Résumé Mensuel")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(1,1,1,1)
        factures_df["mois"] = pd.to_datetime(factures_df["datee"]).dt.month
        ca_par_mois = factures_df.groupby("mois")["mnt_ttc"].sum()
        ca_max = ca_par_mois.max() if not ca_par_mois.empty else 1
        months = ["Janv", "Fév", "Mar", "Avr", "Mai", "Jun",
                  "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
        # --- Ligne 1 : Jan → Juin ---
        row1 = QHBoxLayout()
        for i in range(1, 7):
            row1.addWidget(self._create_month_bar(months[i-1], ca_par_mois.get(i, 0), ca_max))
        layout.addLayout(row1)
        # --- Ligne 2 : Juil → Déc ---
        row2 = QHBoxLayout()
        for i in range(7, 13):
            row2.addWidget(self._create_month_bar(months[i-1], ca_par_mois.get(i, 0), ca_max))
        layout.addLayout(row2)
        return group

    def _create_month_bar(self, label_text, valeur, ca_max):
        bar_widget = QWidget()
        bar_layout = QVBoxLayout(bar_widget)
        bar = QProgressBar()
        bar.setRange(0, ca_max)
        bar.setValue(valeur)
        bar.setFormat(f"{self.cal.separateur_milieur(valeur)}")
        bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                width: 10px;
            }
        """)
        bar_layout.addWidget(bar)
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar_layout.addWidget(label)
        return bar_widget
    def update_data(self, factures_df):
        # --- Calculs ---
        self.ca_total = factures_df["mnt_ttc"].sum() 
        self.montant_paye = factures_df["payer"].sum() 
        self.montant_impaye = factures_df["monn"].sum()
        # --- Cards ---
        self._update_summary_cards(
            total_products=self.ca_total,
            low_stock_alerts=self.montant_paye,
            total_value=self.montant_impaye
        )
        self.update_dashboard(factures_df)

    def _update_summary_cards(self, total_products, low_stock_alerts, total_value):
        # Update labels inside cards
        self.card_total.findChild(QLabel, "SummaryValue").setText(str(total_products))
        self.card_alerts.findChild(QLabel, "SummaryValue").setText(str(low_stock_alerts))
        self.card_value.findChild(QLabel, "SummaryValue").setText(f"{self.cal.separateur_milieur(total_value)} {self.devise}")

    def update_dashboard(self, factures_df):
        # --- Prédiction de la vente du mois prochain ---
        ca_actuel, ca_pred = self.predire_vente_suivante(factures_df)
        if ca_pred:
            delta = ca_pred - ca_actuel
            tendance = "hausse 📈" if delta > 0 else "baisse 📉"
            texte_pred = f"Prévision prochaine: {self.cal.separateur_milieur(ca_pred)} {self.devise} ({tendance})"
            pred_label = QLabel(texte_pred)
            pred_label.setStyleSheet("font-size: 12px; color: yellow; font-weight: bold;")
            self.layout().addWidget(pred_label)

    def calculer_variation(self, factures_df):
        """Variation CA entre mois courant et précédent"""
        factures_df["mois"] = pd.to_datetime(factures_df["datee"]).dt.to_period("M")
        ca_mensuel = factures_df.groupby("mois")["mnt_ttc"].sum().sort_index()

        if len(ca_mensuel) < 2:
            return 0
        ca_courant = ca_mensuel.iloc[-1]
        ca_prec = ca_mensuel.iloc[-2]

        if ca_prec == 0:
            return 0

        variation = ((ca_courant - ca_prec) / ca_prec) * 100
        return round(variation, 1)
    
    
    def resizeEvent(self, event):
        w = self.width()
        h = self.height()

        # Taille proportionnelle des textes
        title_font_size = max(10, int(w / 60))
        card_font_size = max(9, int(w / 80))

        # Titre principal
        for label in self.findChildren(QLabel):
            font = label.font()
            if "ca_total" in label.text() or "Payé" in label.text() or "Impayé" in label.text():
                font.setPointSize(card_font_size)
            else:
                font.setPointSize(title_font_size)
            label.setFont(font)

        # Ajuster taille des légendes de QChart
        for chart_view in self.findChildren(QChartView):
            chart = chart_view.chart()
            chart.setTitleFont(QFont("Arial", title_font_size, QFont.Weight.Bold))
            chart.legend().setFont(QFont("Arial", card_font_size))

        super().resizeEvent(event)

    
    def predire_vente_suivante(self, factures_df):
        """Prédit le chiffre d'affaires du mois prochain avec régression linéaire"""
        # Convertir les dates en périodes mensuelles
        factures_df["mois"] = pd.to_datetime(factures_df["datee"]).dt.to_period("M")

        # Calcul du CA mensuel
        ca_mensuel = factures_df.groupby("mois")["mnt_ttc"].sum().sort_index()

        # Il faut au moins 3 points pour la régression
        if len(ca_mensuel) < 3:
            return None, None

        # Préparer les données
        X = np.arange(len(ca_mensuel)).reshape(-1, 1)
        y = ca_mensuel.values

        # Modèle
        model = LinearRegression()
        model.fit(X, y)

        # Prédire pour le mois suivant
        prochain_index = np.array([[len(ca_mensuel)]])
        prediction = model.predict(prochain_index)[0]

        # Retourner la dernière valeur et la prédiction
        return ca_mensuel.iloc[-1], prediction

