"""Paramètres du modèle. Tous ont été fixés AVANT le test final 2021-2026 (voir docs/methodologie.md)."""

DATA_URL = "https://raw.githubusercontent.com/xgabora/Club-Football-Match-Data-2000-2025/main/data/Matches.csv"

LIGUES = {"E0": "Premier League", "SP1": "Liga", "I1": "Serie A", "D1": "Bundesliga", "F1": "Ligue 1"}
# Deuxièmes divisions : utilisées uniquement pour la forme récente des équipes promues (jamais comme matchs d'apprentissage)
DIV2 = {"E1": "E0", "SP2": "SP1", "I2": "I1", "D2": "D1", "F2": "F1"}
LIGUE_REF = "E0"                      # ligue de référence des indicatrices (effet ligue = 0)
SAISON_MIN = 2005                     # première saison utilisée pour l'apprentissage (2005/06)

# Pondération temporelle : un match d'il y a DEMI_VIE saisons pèse 2 fois moins
DEMI_VIE = 4

# pi-ratings (Constantinou & Fenton 2013) — paramètres de l'article
PI = dict(lr=0.035, gamma=0.7, b=10, c=3)

# Ratings de buts à score GAS (Koopman & Lit 2019) — réglés par vraisemblance sur 2006-2015
GAS = dict(eta=0.0125, eta_l=0.0001, shrink=0.5, mu0=0.262364264467491, ha0=0.15)   # mu0 = log(1.3)

# xG approché : fenêtre de forme (matchs) et centrage de l'ouverture
FENETRE_FORME = 10
CONVERSION_DEFAUT = 0.30          # buts par tir cadré si aucune saison antérieure n'est disponible
OUVERTURE_CENTRE = 5.5
# Niveau de buts de la ligue : 380 derniers matchs, centré
FENETRE_LIGUE = 380
CENTRE_BUTS = (1.5, 1.15)

# Grille des scores
GMAX = 10

# Variables
FE_V3 = ["dElo", "absElo", "dQ", "Otot", "pi_diff", "pi_diff_avg", "lg_SP1", "lg_I1", "lg_D1", "lg_F1"]
FE_V4 = FE_V3 + ["g_lh", "g_la"]                      # modèle 1X2 (v4)
FE_B_V4 = FE_V4 + ["lg_mh_c", "lg_ma_c"]              # modèle de buts (v4)
# v5 : enjeu de fin de saison (course au titre ou au maintien, équipe sans objectif). Voir docs/resultats.md, section v5.
MOTIVATION = ["motiv_h", "motiv_a", "sansenjeu_h", "sansenjeu_a"]
FE = FE_V4 + MOTIVATION                               # modèle 1X2 (v5)
FE_B = FE_B_V4 + MOTIVATION                           # modèle de buts (v5)
FE_B_V3 = FE_V3 + ["lg_mh_c", "lg_ma_c"]

# Corners et cartons (modèles de comptage, à partir de 2008/09 : statistiques complètes)
SAISON_MIN_STATS = 2008
STATS_EQUIPE = ["cf", "ca", "yf", "ya", "rf", "ra", "ff", "fa", "sf", "sa"]   # corners, jaunes, rouges, fautes, tirs (pour / contre)
FE_CORNERS = ["l_lg_c", "h_cf", "h_ca", "a_cf", "a_ca", "dElo", "absElo", "g_lh", "g_la", "h_sf", "a_sf", "h_sa", "a_sa"]
FE_JAUNES = ["l_lg_y", "h_yf", "h_ya", "a_yf", "a_ya", "absElo", "dElo", "h_ff", "a_ff", "h_fa", "a_fa"]
FE_ROUGES = ["l_lg_r", "h_rf", "a_rf", "h_yf", "a_yf", "absElo"]
SEUILS_CORNERS = [7.5, 8.5, 9.5, 10.5, 11.5]
SEUILS_JAUNES = [2.5, 3.5, 4.5, 5.5]
SEUILS_CORNERS_EQUIPE = [3.5, 4.5, 5.5, 6.5]
SEUILS_JAUNES_EQUIPE = [0.5, 1.5, 2.5]

# Découpage du protocole
SAISONS_TEST = [2021, 2022, 2023, 2024, 2025]
