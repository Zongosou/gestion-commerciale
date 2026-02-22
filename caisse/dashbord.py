# from PySide6.QtWidgets import ( QComboBox, QTabWidget, QVBoxLayout, QHBoxLayout,
#     QLabel, QSizePolicy,QGroupBox,QProgressBar,QWidget
# )
# from PySide6.QtCharts import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QLineSeries, QValueAxis

# from PySide6.QtCore import Qt
# from PySide6.QtGui import QIcon,QPainter,QFont
# import pandas as pd
# import numpy as np
# from sklearn.linear_model import LinearRegression
# from fonction.methode import cal
# from stock.gest_stock import SummaryCard


# # ----------- Main Dashboard -----------
# class Dashboard(QWidget):
#     def __init__(self, factures_df, ventes_df,db):
#         super().__init__()
#         self.setWindowTitle("Tableau de Bord")
#         self.setWindowIcon(QIcon(':/icon/314.png'))
#         self.db = db
#         self.ca_total = 0
#         self.montant_paye = 0
#         self.montant_impaye = 0
#         # === 1. Calcul des indicateurs ===
#         self.cal = cal()
#         charge_devise = self.cal.charger_tva_devise(self.db)
#         # Configuration par défaut si non trouvée
#         self.devise = charge_devise["devise"] if charge_devise else "CFA"
#         filter_layout = QHBoxLayout()
#         self.year_combo = QComboBox()
#         self.year_combo.addItem("Toutes les années")

#         annees = pd.to_datetime(factures_df["datee"]).dt.year.unique()
#         for an in sorted(annees):
#             self.year_combo.addItem(str(an))

#         self.year_combo.currentTextChanged.connect(
#             lambda: self.update_data(factures_df)
#         )

#         filter_layout.addWidget(QLabel("Année :"))
#         filter_layout.addWidget(self.year_combo)
#         filter_layout.addStretch()

        
#         self.dashboard_cards = self.create_dashboard_cards()
#         main_layout = QVBoxLayout()
#         main_layout.addWidget(self.dashboard_cards)
#         main_layout.addLayout(filter_layout)
#         self.pred_label = QLabel("")
#         self.pred_label.setStyleSheet(
#             "font-size: 13px; font-weight: bold; padding:4px;"
#         )
#         main_layout.addWidget(self.pred_label)
#         # Créer une disposition horizontale pour les deux derniers graphiques
#         bottom_graphs_layout = QHBoxLayout()

#         # bottom_graphs_layout.addWidget(canvas3)
#         main_layout.addWidget(self.create_monthly_summary(factures_df))
#         # ===  Top 5 Clients ===
#         bottom_graphs_layout.addWidget(self.create_top5_clients_chart(ventes_df), 1)
#         bottom_graphs_layout.addWidget(self.create_top5_produits_chart(ventes_df), 1)
#         bottom_graphs_layout.addWidget(self.create_ca_line_chart(factures_df))
#         # Ajouter le layout horizontal à la disposition principale
        
#         main_layout.addLayout(bottom_graphs_layout)
#         self.setLayout(main_layout)
#         self.update_data(factures_df)
#         # Graphique ventes mensuelles
        
#     def create_marge_line_chart(self, factures_df):

#         if "marge" not in factures_df.columns:
#             return QLabel("Pas de données marge")

#         df = factures_df.copy()

#         if self.year_combo.currentText() != "Toutes les années":
#             annee = int(self.year_combo.currentText())
#             df = df[pd.to_datetime(df["datee"]).dt.year == annee]

#         df["mois"] = pd.to_datetime(df["datee"]).dt.month
#         marge_mensuelle = df.groupby("mois")["marge"].sum()

#         series = QLineSeries()

#         for mois, valeur in marge_mensuelle.items():
#             series.append(mois, valeur)

#         chart = QChart()
#         chart.addSeries(series)
#         chart.setTitle("Évolution Marge Mensuelle")

#         axisX = QValueAxis()
#         axisX.setRange(1, 12)
#         axisX.setTitleText("Mois")

#         axisY = QValueAxis()
#         axisY.setTitleText(f"Marge ({self.devise})")

#         chart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
#         chart.addAxis(axisY, Qt.AlignmentFlag.AlignLeft)

#         series.attachAxis(axisX)
#         series.attachAxis(axisY)

#         chart_view = QChartView(chart)
#         chart_view.setRenderHint(QPainter.Antialiasing)

#         return chart_view
#     def create_ca_line_chart(self, factures_df):

#         df = factures_df.copy()

#         if self.year_combo.currentText() != "Toutes les années":
#             annee = int(self.year_combo.currentText())
#             df = df[pd.to_datetime(df["datee"]).dt.year == annee]

#         df["mois"] = pd.to_datetime(df["datee"]).dt.month
#         ca_mensuel = df.groupby("mois")["mnt_ttc"].sum()

#         series = QLineSeries()

#         for mois, valeur in ca_mensuel.items():
#             series.append(mois, valeur)

#         chart = QChart()
#         chart.addSeries(series)
#         chart.setTitle("Évolution CA Mensuel")

#         axisX = QValueAxis()
#         axisX.setRange(1, 12)
#         axisX.setLabelFormat("%d")
#         axisX.setTitleText("Mois")

#         axisY = QValueAxis()
#         axisY.setTitleText(f"CA ({self.devise})")

#         chart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
#         chart.addAxis(axisY, Qt.AlignmentFlag.AlignLeft)

#         series.attachAxis(axisX)
#         series.attachAxis(axisY)

#         chart_view = QChartView(chart)
#         chart_view.setRenderHint(QPainter.Antialiasing)

#         return chart_view
            
#     def create_top5_produits_chart(self, ventes_df):
#         """Crée un QChart pour Top 5 Produits"""
#         try:
#             top_produits = ventes_df.groupby("libelle")["montant"].sum().nlargest(5)

#             set0 = QBarSet("Produits")
#             set0.append(top_produits.values.tolist())

#             series = QBarSeries()
#             series.append(set0)

#             chart = QChart()
#             chart.addSeries(series)
#             chart.setTitle("Top 5 Produits les plus vendus (CA)")
#             chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
#             axisX = QBarCategoryAxis()
#             axisX.append(top_produits.index.tolist())
#             chart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
#             series.attachAxis(axisX)
#             axisY = QValueAxis()
#             axisY.setTitleText(f"Montant ({self.devise})")
#             chart.addAxis(axisY, Qt.AlignmentFlag.AlignLeft)
#             series.attachAxis(axisY)

#             chart.legend().setVisible(False)
#             chart_view = QChartView(chart)
#             chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
#         except Exception as e:
#             print(f"Erreur lors de la création du graphique Top 5 Produits: {e}")
#             chart_view = QLabel("Aucune donnée disponible pour les produits.")
#             chart_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         return chart_view

#     def create_top5_clients_chart(self, ventes_df):
#         """Crée un QChart pour Top 5 Clients"""
#         try:
#             top_clients = ventes_df.groupby("client")["montant"].sum().nlargest(5)

#             set0 = QBarSet("Clients")
#             set0.append(top_clients.values.tolist())

#             series = QBarSeries()
#             series.append(set0)

#             chart = QChart()
#             chart.addSeries(series)
#             chart.setTitle("Top 5 Clients (CA)")
#             chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

#             axisX = QBarCategoryAxis()
#             axisX.append(top_clients.index.tolist())
#             chart.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
#             series.attachAxis(axisX)
#             axisY = QValueAxis()
#             axisY.setTitleText(f"Montant ({self.devise})")
#             chart.addAxis(axisY, Qt.AlignmentFlag.AlignLeft)
#             series.attachAxis(axisY)

#             # chart.axisY().setTitleText(f"Montant {self.devise}")

#             chart.legend().setVisible(False)
#             chart_view = QChartView(chart)
#             chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
#         except Exception as e:
#             print(f"Erreur lors de la création du graphique Top 5 Clients: {e}")
#             chart_view = QLabel("Aucune donnée disponible pour les clients.")
#             chart_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         return chart_view

            
#     def create_dashboard_cards(self):
#         widget = QWidget()
#         # ================= CARTES =================
#         cards_row = QHBoxLayout(widget)
#         self.card_total = SummaryCard("Revenu Total", "0.0", accent="#2D7EF7")
#         self.card_alerts = SummaryCard("Montant Payé", "0.0", accent="#F59E0B")
#         self.card_value = SummaryCard("Montant Restant", "0.0", accent="#10B981")
#         self.card_marge = SummaryCard("Marge Totale", "0.0", accent="#8B5CF6")

#         for card in (
#             self.card_total,
#             self.card_alerts,
#             self.card_value,
#             self.card_marge
#         ):
#             cards_row.addWidget(card, 1)
#         # layout.addLayout(cards_row)
#         return widget

#     def create_monthly_summary(self, factures_df):
#         group = QGroupBox("Résumé Mensuel")
#         layout = QVBoxLayout(group)
#         layout.setContentsMargins(1,1,1,1)
#         factures_df["mois"] = pd.to_datetime(factures_df["datee"]).dt.month
#         ca_par_mois = factures_df.groupby("mois")["mnt_ttc"].sum()
#         ca_max = ca_par_mois.max() if not ca_par_mois.empty else 1
#         months = ["Janv", "Fév", "Mar", "Avr", "Mai", "Jun",
#                   "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
#         # --- Ligne 1 : Jan → Juin ---
#         row1 = QHBoxLayout()
#         for i in range(1, 7):
#             row1.addWidget(self._create_month_bar(months[i-1], ca_par_mois.get(i, 0), ca_max))
#         layout.addLayout(row1)
#         # --- Ligne 2 : Juil → Déc ---
#         row2 = QHBoxLayout()
#         for i in range(7, 13):
#             row2.addWidget(self._create_month_bar(months[i-1], ca_par_mois.get(i, 0), ca_max))
#         layout.addLayout(row2)
#         return group

#     def _create_month_bar(self, label_text, valeur, ca_max):
#         bar_widget = QWidget()
#         bar_layout = QVBoxLayout(bar_widget)
#         bar = QProgressBar()
#         bar.setRange(0, ca_max)
#         bar.setValue(valeur)
#         bar.setFormat(f"{self.cal.separateur_milieur(valeur)}")
#         bar.setStyleSheet("""
#             QProgressBar {
#                 border: 1px solid #ddd;
#                 border-radius: 5px;
#                 text-align: center;
#             }
#             QProgressBar::chunk {
#                 background-color: #2ecc71;
#                 width: 10px;
#             }
#         """)
#         bar_layout.addWidget(bar)
#         label = QLabel(label_text)
#         label.setAlignment(Qt.AlignmentFlag.AlignCenter)
#         bar_layout.addWidget(label)
#         return bar_widget
#     def update_data(self, factures_df):
#         # --- Calculs ---
#         self.ca_total = factures_df["mnt_ttc"].sum() 
#         self.montant_paye = factures_df["payer"].sum() 
#         self.montant_impaye = factures_df["monn"].sum()
#         self.marge_totale = factures_df["marge"].sum() if "marge" in factures_df else 0

        

#         self.card_marge.findChild(QLabel, "SummaryValue").setText(
#             f"{self.cal.separateur_milieur(self.marge_totale)} {self.devise}"
#         )
#         variation = self.calculer_variation(factures_df)

#         if variation > 0:
#             self.card_total.setStyleSheet("border-left: 5px solid green;")
#         else:
#             self.card_total.setStyleSheet("border-left: 5px solid red;")
#         # --- Cards ---
#         self._update_summary_cards(
#             total_products=self.ca_total,
#             low_stock_alerts=self.montant_paye,
#             total_value=self.montant_impaye
#         )
#         self.update_dashboard(factures_df)

#     def _update_summary_cards(self, total_products, low_stock_alerts, total_value):
#         # Update labels inside cards
#         self.card_total.findChild(QLabel, "SummaryValue").setText(
#             f"{self.cal.separateur_milieur(total_products)} {self.devise}"
#         )

#         self.card_alerts.findChild(QLabel, "SummaryValue").setText(
#             f"{self.cal.separateur_milieur(low_stock_alerts)} {self.devise}"
#         )

#         self.card_value.findChild(QLabel, "SummaryValue").setText(
#             f"{self.cal.separateur_milieur(total_value)} {self.devise}"
#         )

#     def update_dashboard(self, factures_df):
#         # --- Prédiction de la vente du mois prochain ---
#         ca_actuel, ca_pred = self.predire_vente_suivante(factures_df)
#         if ca_pred:
#             delta = ca_pred - ca_actuel
#             tendance = "📈 Hausse" if delta > 0 else "📉 Baisse"
#             self.pred_label.setText(
#                 f"Prévision prochaine : "
#                 f"{self.cal.separateur_milieur(ca_pred)} {self.devise} "
#                 f"({tendance})"
#             )

#     def calculer_variation(self, factures_df):
#         """Variation CA entre mois courant et précédent"""
#         factures_df["mois"] = pd.to_datetime(factures_df["datee"]).dt.to_period("M")
#         ca_mensuel = factures_df.groupby("mois")["mnt_ttc"].sum().sort_index()

#         if len(ca_mensuel) < 2:
#             return 0
#         ca_courant = ca_mensuel.iloc[-1]
#         ca_prec = ca_mensuel.iloc[-2]

#         if ca_prec == 0:
#             return 0

#         variation = ((ca_courant - ca_prec) / ca_prec) * 100
#         return round(variation, 1)
    
    
#     def resizeEvent(self, event):
#         w = self.width()
#         h = self.height()

#         # Taille proportionnelle des textes
#         title_font_size = max(10, int(w / 60))
#         card_font_size = max(9, int(w / 80))

#         # Titre principal
#         for label in self.findChildren(QLabel):
#             font = label.font()
#             if "ca_total" in label.text() or "Payé" in label.text() or "Impayé" in label.text():
#                 font.setPointSize(card_font_size)
#             else:
#                 font.setPointSize(title_font_size)
#             label.setFont(font)

#         # Ajuster taille des légendes de QChart
#         for chart_view in self.findChildren(QChartView):
#             chart = chart_view.chart()
#             chart.setTitleFont(QFont("Arial", title_font_size, QFont.Weight.Bold))
#             chart.legend().setFont(QFont("Arial", card_font_size))

#         super().resizeEvent(event)

    
#     def predire_vente_suivante(self, factures_df):
#         """Prédit le chiffre d'affaires du mois prochain avec régression linéaire"""
#         # Convertir les dates en périodes mensuelles
#         factures_df["mois"] = pd.to_datetime(factures_df["datee"]).dt.to_period("M")

#         # Calcul du CA mensuel
#         ca_mensuel = factures_df.groupby("mois")["mnt_ttc"].sum().sort_index()

#         # Il faut au moins 3 points pour la régression
#         if len(ca_mensuel) < 3:
#             return None, None

#         # Préparer les données
#         X = np.arange(len(ca_mensuel)).reshape(-1, 1)
#         y = ca_mensuel.values

#         # Modèle
#         model = LinearRegression()
#         model.fit(X, y)

#         # Prédire pour le mois suivant
#         prochain_index = np.array([[len(ca_mensuel)]])
#         prediction = model.predict(prochain_index)[0]

#         # Retourner la dernière valeur et la prédiction
#         return ca_mensuel.iloc[-1], prediction

from PySide6.QtWidgets import (
    QScrollArea, QSizePolicy, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QProgressBar, QComboBox
)
from PySide6.QtCharts import (
    QChart, QChartView, QBarSet, QBarSeries,
    QBarCategoryAxis, QValueAxis, QLineSeries
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPen, QColor
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from fonction.methode import cal
from stock.gest_stock import SummaryCard


class Dashboard(QWidget):

    def __init__(self, factures_df, ventes_df, db):
        super().__init__()
        self.setWindowTitle("Tableau de Bord BI")
        self.db = db
        self.cal = cal()

        config = self.cal.charger_tva_devise(self.db)
        self.devise = config["devise"] if config else "CFA"

        

        outer_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        outer_layout.addWidget(scroll)

        # Conteneur interne
        container = QWidget()
        scroll.setWidget(container)

        main_layout = QVBoxLayout(container)

        # ================= FILTRE ANNEE =================
        filter_layout = QHBoxLayout()
        self.year_combo = QComboBox()
        self.year_combo.addItem("Toutes les années")

        annees = pd.to_datetime(factures_df["datee"]).dt.year.unique()
        for an in sorted(annees):
            self.year_combo.addItem(str(an))

        self.year_combo.currentTextChanged.connect(
            lambda: self.update_data(factures_df, ventes_df)
        )

        filter_layout.addWidget(QLabel("Année :"))
        filter_layout.addWidget(self.year_combo)
        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)

        # ================= CARDS =================
        self.cards_widget = self.create_dashboard_cards()
        main_layout.addWidget(self.cards_widget)

        # ================= COURBES =================
        self.ca_chart_view = self.create_ca_line_chart(factures_df)
        self.marge_chart_view = self.create_marge_line_chart(factures_df)
        self.ca_chart_view.setMinimumHeight(350)
        self.marge_chart_view.setMinimumHeight(350)
        main_layout.addWidget(self.ca_chart_view)
        main_layout.addWidget(self.marge_chart_view)

        # ================= TOP 5 =================
        bottom_layout = QHBoxLayout()
        
        bottom_layout.addWidget(self.create_top5_clients_chart(ventes_df))
        bottom_layout.addWidget(self.create_top5_produits_chart(ventes_df))
        main_layout.addLayout(bottom_layout)

        # ================= PREDICTION =================
        self.pred_label = QLabel("")
        self.pred_label.setStyleSheet(
            "font-size: 13px; font-weight: bold; padding:4px;"
        )
        main_layout.addWidget(self.pred_label)

        self.update_data(factures_df, ventes_df)

    # =====================================================
    # ================= CARDS =============================
    # =====================================================

    def create_dashboard_cards(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)

        self.card_total = SummaryCard("Revenu Total", "0", accent="#2D7EF7")
        self.card_paye = SummaryCard("Montant Payé", "0", accent="#F59E0B")
        self.card_impaye = SummaryCard("Montant Restant", "0", accent="#10B981")
        self.card_marge = SummaryCard("Marge Totale", "0", accent="#8B5CF6")

        for card in (
            self.card_total,
            self.card_paye,
            self.card_impaye,
            self.card_marge
        ):
            layout.addWidget(card, 1)

        return widget

    # =====================================================
    # ================= COURBE CA =========================
    # =====================================================

    def create_ca_line_chart(self, factures_df):

        df = self._filter_year(factures_df)

        df["mois"] = pd.to_datetime(df["datee"]).dt.month
        ca_mensuel = df.groupby("mois")["mnt_ttc"].sum()

        series = QLineSeries()
        pen = QPen(QColor("#2D7EF7"))
        pen.setWidth(3)
        series.setPen(pen)

        for mois in range(1, 13):
            series.append(mois, ca_mensuel.get(mois, 0))

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Évolution du Chiffre d’Affaires")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        axisX = QValueAxis()
        axisX.setRange(1, 12)
        axisX.setTitleText("Mois")

        axisY = QValueAxis()
        axisY.setTitleText(f"CA ({self.devise})")

        chart.addAxis(axisX, Qt.AlignBottom)
        chart.addAxis(axisY, Qt.AlignLeft)

        series.attachAxis(axisX)
        series.attachAxis(axisY)

        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(350)

        return view

    # =====================================================
    # ================= COURBE MARGE ======================
    # =====================================================

    def create_marge_line_chart(self, factures_df):

        if "marge" not in factures_df.columns:
            return QLabel("Pas de données marge")

        df = self._filter_year(factures_df)

        df["mois"] = pd.to_datetime(df["datee"]).dt.month
        marge_mensuelle = df.groupby("mois")["marge"].sum()

        series = QLineSeries()
        pen = QPen(QColor("#8B5CF6"))
        pen.setWidth(3)
        series.setPen(pen)

        for mois in range(1, 13):
            series.append(mois, marge_mensuelle.get(mois, 0))

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Évolution de la Marge")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        axisX = QValueAxis()
        axisX.setRange(1, 12)
        axisX.setTitleText("Mois")

        axisY = QValueAxis()
        axisY.setTitleText(f"Marge ({self.devise})")

        chart.addAxis(axisX, Qt.AlignBottom)
        chart.addAxis(axisY, Qt.AlignLeft)

        series.attachAxis(axisX)
        series.attachAxis(axisY)

        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(350)

        return view

    # =====================================================
    # ================= TOP 5 CLIENTS =====================
    # =====================================================

    def create_top5_clients_chart(self, ventes_df):

        top_clients = ventes_df.groupby("client")["montant"].sum().nlargest(5)

        set0 = QBarSet("Clients")
        set0.append(top_clients.values.tolist())

        series = QBarSeries()
        series.append(set0)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Top 5 Clients")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        axisX = QBarCategoryAxis()
        axisX.append(top_clients.index.tolist())

        axisY = QValueAxis()
        axisY.setTitleText(f"Montant ({self.devise})")

        chart.addAxis(axisX, Qt.AlignBottom)
        chart.addAxis(axisY, Qt.AlignLeft)

        series.attachAxis(axisX)
        series.attachAxis(axisY)

        chart.legend().setVisible(False)

        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(350)
        view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        return view

    # =====================================================
    # ================= TOP 5 PRODUITS ====================
    # =====================================================

    def create_top5_produits_chart(self, ventes_df):

        top_produits = ventes_df.groupby("libelle")["montant"].sum().nlargest(5)

        set0 = QBarSet("Produits")
        set0.append(top_produits.values.tolist())

        series = QBarSeries()
        series.append(set0)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Top 5 Produits")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        axisX = QBarCategoryAxis()
        axisX.append(top_produits.index.tolist())

        axisY = QValueAxis()
        axisY.setTitleText(f"Montant ({self.devise})")

        chart.addAxis(axisX, Qt.AlignBottom)
        chart.addAxis(axisY, Qt.AlignLeft)

        series.attachAxis(axisX)
        series.attachAxis(axisY)

        chart.legend().setVisible(False)

        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(350)
        view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        return view

    # =====================================================
    # ================= UPDATE ============================
    # =====================================================

    def update_data(self, factures_df, ventes_df):

        df = self._filter_year(factures_df)

        ca_total = df["mnt_ttc"].sum()
        montant_paye = df["payer"].sum()
        montant_impaye = df["monn"].sum()
        marge_totale = df["marge"].sum() if "marge" in df else 0

        self.card_total.findChild(QLabel, "SummaryValue").setText(
            f"{self.cal.separateur_milieur(ca_total)} {self.devise}"
        )
        self.card_paye.findChild(QLabel, "SummaryValue").setText(
            f"{self.cal.separateur_milieur(montant_paye)} {self.devise}"
        )
        self.card_impaye.findChild(QLabel, "SummaryValue").setText(
            f"{self.cal.separateur_milieur(montant_impaye)} {self.devise}"
        )
        self.card_marge.findChild(QLabel, "SummaryValue").setText(
            f"{self.cal.separateur_milieur(marge_totale)} {self.devise}"
        )

        self._update_prediction(df)

    # =====================================================

    def _filter_year(self, df):
        if self.year_combo.currentText() == "Toutes les années":
            return df.copy()
        annee = int(self.year_combo.currentText())
        return df[pd.to_datetime(df["datee"]).dt.year == annee]

    def _update_prediction(self, df):

        df["mois"] = pd.to_datetime(df["datee"]).dt.to_period("M")
        ca_mensuel = df.groupby("mois")["mnt_ttc"].sum().sort_index()
        print("Nombre de mois :", len(ca_mensuel))
        if len(ca_mensuel) < 3:
            self.pred_label.setText("")
            return

        X = np.arange(len(ca_mensuel)).reshape(-1, 1)
        y = ca_mensuel.values

        model = LinearRegression()
        model.fit(X, y)

        prediction = model.predict([[len(ca_mensuel)]])[0]
        delta = prediction - ca_mensuel.iloc[-1]

        tendance = "📈 Hausse" if delta > 0 else "📉 Baisse"

        self.pred_label.setText(
            f"Prévision mois prochain : "
            f"{self.cal.separateur_milieur(round(prediction,2))} {self.devise} "
            f"({tendance})"
        )