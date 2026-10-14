# Résultats du banc d'essai v6 (généré par `scripts/banc_evaluer.py`, 2026-10-13)

Prédictions hors échantillon strictement chronologiques (`footpred/banc.py`). Fenêtre A = 2016-2020, B = 2021-2024 (validation : empilement par fenêtre glissante, méta-modèle, seuils), T = 2025/26 (test final réservé, aucune décision n'y est prise). Les variables de v5 ont été étudiées sur 2010-2025 : T n'est donc pas totalement vierge pour E0 ; l'évaluation prospective est le journal 2026/27.

## 1. Ensembles appris par fenêtre glissante

|   saison test |   E0 Goalgebra v5 (logit) · log(P1/PX) |   E1 Logistique Elo + forme · log(P1/PX) |   E2 Dixon-Coles (buts) · log(P1/PX) |   E3 CatBoost (sport) · log(P1/PX) |
|--------------:|---------------------------------------:|-----------------------------------------:|-------------------------------------:|-----------------------------------:|
|          2021 |                                  0.324 |                                    0.199 |                                0.513 |                             -0.008 |
|          2022 |                                  0.408 |                                    0.134 |                                0.471 |                              0.029 |
|          2023 |                                  0.312 |                                    0.294 |                                0.492 |                             -0.022 |
|          2024 |                                  0.423 |                                    0.238 |                                0.383 |                              0.01  |
|          2025 |                                  0.459 |                                    0.113 |                                0.494 |                             -0.009 |

Coefficients de l'empilement (log P1/PX) par saison de test : leur stabilité indique si l'ensemble est robuste.

## 2. Matrice d'expériences sur les mêmes matchs (cotes disponibles)


### validation B 2021-2024 — 7144 matchs communs

|                                 |    n |   log loss |   Brier |    RPS |    ECE |   accuracy |   macro F1 |   rappel 1 |   rappel X |   rappel 2 |
|:--------------------------------|-----:|-----------:|--------:|-------:|-------:|-----------:|-----------:|-----------:|-----------:|-----------:|
| Classe majoritaire (fréquences) | 7144 |     1.074  |  0.65   | 0.2302 | 0.0091 |     0.4341 |     0.2018 |     1      |     0      |     0      |
| E0 Goalgebra v5 (logit)         | 7144 |     0.9792 |  0.5832 | 0.1982 | 0.0145 |     0.5284 |     0.3983 |     0.7981 |     0.005  |     0.5794 |
| Elo seul                        | 7144 |     0.9825 |  0.5856 | 0.1989 | 0.0157 |     0.5281 |     0.393  |     0.8243 |     0      |     0.5462 |
| E1 Logistique Elo + forme       | 7144 |     0.9805 |  0.5841 | 0.1983 | 0.0209 |     0.5329 |     0.3975 |     0.8239 |     0      |     0.5619 |
| E2 Dixon-Coles (buts)           | 7144 |     0.9804 |  0.5839 | 0.1984 | 0.017  |     0.528  |     0.3954 |     0.7949 |     0      |     0.5866 |
| E3 CatBoost (sport)             | 7144 |     0.9819 |  0.5851 | 0.1988 | 0.014  |     0.5265 |     0.3972 |     0.8033 |     0.0061 |     0.5651 |
| E5 Marché seul (Shin)           | 7144 |     0.9686 |  0.576  | 0.1947 | 0.0139 |     0.5382 |     0.4033 |     0.8178 |     0.0011 |     0.5866 |
| E6 Sport + marché (empilement)  | 7144 |     0.9687 |  0.5761 | 0.1946 | 0.0125 |     0.5385 |     0.4037 |     0.8204 |     0.0017 |     0.5835 |
| E7 Ensemble sport calibré       | 7144 |     0.9804 |  0.5839 | 0.1984 | 0.0142 |     0.5291 |     0.3969 |     0.7868 |     0      |     0.6014 |
| comparaison                                            |   Δ log loss ×1e3 |   IC bas |   IC haut | significatif   |
|:-------------------------------------------------------|------------------:|---------:|----------:|:---------------|
| E7 Ensemble sport calibré − E0 Goalgebra v5 (logit)    |              1.21 |     0.12 |      2.33 | oui            |
| E3 CatBoost (sport) − E0 Goalgebra v5 (logit)          |              2.69 |     0.7  |      4.66 | oui            |
| E2 Dixon-Coles (buts) − E0 Goalgebra v5 (logit)        |              1.25 |    -0.19 |      2.63 | non            |
| E0 Goalgebra v5 (logit) − Elo seul                     |             -3.35 |    -6.16 |     -0.53 | oui            |
| E6 Sport + marché (empilement) − E5 Marché seul (Shin) |              0.18 |    -0.58 |      0.91 | non            |
| E7 Ensemble sport calibré − E5 Marché seul (Shin)      |             11.82 |     8.81 |     14.85 | oui            |

### test final T 2025-26 — 1752 matchs communs

|                                 |    n |   log loss |   Brier |    RPS |    ECE |   accuracy |   macro F1 |   rappel 1 |   rappel X |   rappel 2 |
|:--------------------------------|-----:|-----------:|--------:|-------:|-------:|-----------:|-----------:|-----------:|-----------:|-----------:|
| Classe majoritaire (fréquences) | 1752 |     1.0718 |  0.6483 | 0.2293 | 0      |     0.4401 |     0.2037 |     1      |     0      |     0      |
| E0 Goalgebra v5 (logit)         | 1752 |     0.9884 |  0.5893 | 0.2007 | 0.0307 |     0.5183 |     0.3959 |     0.7847 |     0.0179 |     0.5514 |
| Elo seul                        | 1752 |     0.9961 |  0.5944 | 0.2033 | 0.0258 |     0.5131 |     0.3799 |     0.7977 |     0      |     0.5308 |
| E1 Logistique Elo + forme       | 1752 |     0.9909 |  0.5911 | 0.2017 | 0.019  |     0.5148 |     0.3822 |     0.7925 |     0      |     0.5439 |
| E2 Dixon-Coles (buts)           | 1752 |     0.9897 |  0.59   | 0.2012 | 0.0215 |     0.516  |     0.3835 |     0.7899 |     0      |     0.5514 |
| E3 CatBoost (sport)             | 1752 |     0.9897 |  0.5904 | 0.2013 | 0.0283 |     0.52   |     0.4005 |     0.7795 |     0.0224 |     0.5607 |
| E5 Marché seul (Shin)           | 1752 |     0.9784 |  0.5824 | 0.1976 | 0.0271 |     0.5331 |     0.3971 |     0.8262 |     0.0022 |     0.5533 |
| E6 Sport + marché (empilement)  | 1752 |     0.978  |  0.5821 | 0.1974 | 0.0283 |     0.5371 |     0.4029 |     0.8249 |     0.0067 |     0.5645 |
| E7 Ensemble sport calibré       | 1752 |     0.9896 |  0.5901 | 0.2012 | 0.031  |     0.516  |     0.3871 |     0.7678 |     0.0022 |     0.5813 |
| comparaison                                            |   Δ log loss ×1e3 |   IC bas |   IC haut | significatif   |
|:-------------------------------------------------------|------------------:|---------:|----------:|:---------------|
| E7 Ensemble sport calibré − E0 Goalgebra v5 (logit)    |              1.2  |    -0.74 |      3.22 | non            |
| E3 CatBoost (sport) − E0 Goalgebra v5 (logit)          |              1.3  |    -2.8  |      5.32 | non            |
| E2 Dixon-Coles (buts) − E0 Goalgebra v5 (logit)        |              1.29 |    -1.93 |      4.63 | non            |
| E0 Goalgebra v5 (logit) − Elo seul                     |             -7.67 |   -13.37 |     -1.96 | oui            |
| E6 Sport + marché (empilement) − E5 Marché seul (Shin) |             -0.4  |    -2.3  |      1.4  | non            |
| E7 Ensemble sport calibré − E5 Marché seul (Shin)      |             11.18 |     4.89 |     17.86 | oui            |

Matrice de confusion E7 (lignes = réel 1/X/2, colonnes = prédit) :

|        |   prédit 1 |   prédit X |   prédit 2 |
|:-------|-----------:|-----------:|-----------:|
| réel 1 |        592 |          2 |        177 |
| réel X |        263 |          1 |        182 |
| réel 2 |        222 |          2 |        311 |

## 3. Stabilité par saison (log loss, mêmes matchs)

| saison   |   Elo seul |   E0 Goalgebra v5 (logit) |   E2 Dixon-Coles (buts) |   E3 CatBoost (sport) |   E7 Ensemble sport calibré |   E6 Sport + marché (empilement) |   E5 Marché seul (Shin) |
|:---------|-----------:|--------------------------:|------------------------:|----------------------:|----------------------------:|---------------------------------:|------------------------:|
| 2021/22  |     0.9897 |                    0.9858 |                  0.9875 |                0.989  |                      0.9877 |                           0.9779 |                  0.9773 |
| 2022/23  |     0.9838 |                    0.987  |                  0.9859 |                0.9861 |                      0.9881 |                           0.9791 |                  0.9776 |
| 2023/24  |     0.9708 |                    0.9659 |                  0.9707 |                0.9681 |                      0.9684 |                           0.9538 |                  0.9545 |
| 2024/25  |     0.9855 |                    0.9773 |                  0.977  |                0.9838 |                      0.9767 |                           0.9633 |                  0.9641 |
| 2025/26  |     0.9961 |                    0.9884 |                  0.9897 |                0.9897 |                      0.9896 |                           0.978  |                  0.9784 |

## 4. Méthodes de calibration de E0 (apprises sur les saisons antérieures)

|                 |    n |   log loss |   Brier |    ECE |
|:----------------|-----:|-----------:|--------:|-------:|
| E0 brut         | 8897 |     0.981  |  0.5844 | 0.0113 |
| E0 température  | 8897 |     0.9811 |  0.5844 | 0.0109 |
| E0 multinomiale | 8897 |     0.9818 |  0.5849 | 0.0146 |
| E0 isotonique   | 8897 |     0.9863 |  0.5857 | 0.0144 |
|             |   pente |   intercept |
|:------------|--------:|------------:|
| ('E0', '1') |   0.998 |       0.002 |
| ('E0', 'X') |   0.95  |      -0.037 |
| ('E0', '2') |   0.984 |      -0.03  |
| ('E7', '1') |   1.016 |       0.049 |
| ('E7', 'X') |   1.029 |       0.057 |
| ('E7', '2') |   0.99  |      -0.082 |

Pente 1 et intercept 0 = calibration parfaite ; pente < 1 = probabilités trop extrêmes.

## 5. Ablations du modèle v5 (Δ log loss ×1e3 par rapport au modèle complet ; > 0 = la famille retirée était utile)

|                                             |   Δ ×1e3 |   IC bas |   IC haut | significatif   |
|:--------------------------------------------|---------:|---------:|----------:|:---------------|
| ('sans Elo', 'B 2021-2024')                 |     1.29 |     0.05 |      2.53 | oui            |
| ('sans Elo', 'T 2025-26')                   |     0.23 |    -2.31 |      2.68 | non            |
| ('sans forme / xG proxy', 'B 2021-2024')    |     2.15 |     0.4  |      3.93 | oui            |
| ('sans forme / xG proxy', 'T 2025-26')      |     4.29 |     0.77 |      7.7  | oui            |
| ('sans pi-ratings', 'B 2021-2024')          |    -0.05 |    -0.68 |      0.57 | non            |
| ('sans pi-ratings', 'T 2025-26')            |     0.04 |    -1.05 |      1.17 | non            |
| ('sans ratings de buts GAS', 'B 2021-2024') |     0.27 |    -0.95 |      1.44 | non            |
| ('sans ratings de buts GAS', 'T 2025-26')   |     0.54 |    -1.81 |      2.91 | non            |
| ('sans contexte (enjeu)', 'B 2021-2024')    |     0.23 |    -0.65 |      1.13 | non            |
| ('sans contexte (enjeu)', 'T 2025-26')      |     0.15 |    -1.83 |      2.16 | non            |
| ('sans effets ligue', 'B 2021-2024')        |     0.26 |    -0.32 |      0.88 | non            |
| ('sans effets ligue', 'T 2025-26')          |     0.11 |    -1.17 |      1.41 | non            |

Sans xG fournisseur (E4) : non réalisé, aucune source gratuite et fiable joignable ; la famille « forme / xG proxy » correspond au xG approché (tirs cadrés × conversion). Variables événementielles : étude séparée (resultats.md §13).

## 6. Moteur de sélection : distribution conjointe cohérente, méta-modèle, seuils (validation B), test T


Source des probabilités 1X2 retenue sur la validation B : **E0 Goalgebra v5 (logit)** (log loss B : E0 0.9792, E7 0.9804). Un ensemble qui n'améliore pas la validation n'est pas utilisé.
|                           |   coefficient |   erreur type |
|:--------------------------|--------------:|--------------:|
| constante                 |        -0.023 |         0.059 |
| logit(p)                  |         1.016 |         0.009 |
| famille Buts              |        -0.009 |         0.023 |
| famille Double chance     |        -0.02  |         0.025 |
| famille Les deux marquent |        -0.009 |         0.024 |
| famille Remboursé si nul  |        -0.01  |         0.028 |
| famille Équipe marque     |         0.051 |         0.029 |
| désaccord                 |         0.041 |         0.291 |
| entropie                  |         0.022 |         0.058 |
| saison installée          |         0.012 |         0.019 |
| cotes disponibles         |         0     |         0     |

Seuils choisis sur la validation B (cibles : retenues ≥ 85%, prudentes ≥ 75%, dans chaque saison, écart de calibration ≥ −2 points ; objectif : couverture maximale) : `{"p_bas_min": 0.79, "info_min": 0.02, "desaccord_max": 1.0, "p_prudente_min": 0.69}`

### validation B — mode « compromis »

|                                        |   matchs |   couverture |   réussite |   p moyenne annoncée |   référence moyenne |   succès en plus de la référence |   borne basse moyenne |   log loss |   Brier |   information publiée (bits) |
|:---------------------------------------|---------:|-------------:|-----------:|---------------------:|--------------------:|---------------------------------:|----------------------:|-----------:|--------:|-----------------------------:|
| retenue                                |     4177 |       0.5846 |     0.868  |               0.871  |              0.733  |                           0.1349 |                0.8592 |     0.3833 |  0.1131 |                     385.777  |
| prudente                               |     1234 |       0.1727 |     0.773  |               0.7798 |              0.6872 |                           0.0858 |                0.7657 |     0.5307 |  0.1736 |                      39.1014 |
| abstention                             |     1734 |       0.2427 |     0.9348 |               0.9202 |              0.9323 |                           0.0025 |                0.9132 |     0.242  |  0.0611 |                       0      |
| tous les matchs (1X2 le plus probable) |     7145 |       1      |     0.5283 |               0.5326 |              0.5268 |                           0.0016 |                0.4998 |     0.6583 |  0.2333 |                      73.9663 |

### validation B — mode « probable »

|                                        |   matchs |   couverture |   réussite |   p moyenne annoncée |   référence moyenne |   succès en plus de la référence |   borne basse moyenne |   log loss |   Brier |   information publiée (bits) |
|:---------------------------------------|---------:|-------------:|-----------:|---------------------:|--------------------:|---------------------------------:|----------------------:|-----------:|--------:|-----------------------------:|
| retenue                                |     4177 |       0.5846 |     0.8736 |               0.8734 |              0.7488 |                           0.1248 |                0.862  |     0.3692 |  0.1085 |                     321.824  |
| prudente                               |     1234 |       0.1727 |     0.78   |               0.7815 |              0.6898 |                           0.0901 |                0.7681 |     0.5236 |  0.1704 |                      38.112  |
| abstention                             |     1734 |       0.2427 |     0.9348 |               0.9202 |              0.9323 |                           0.0025 |                0.9132 |     0.242  |  0.0611 |                       0      |
| tous les matchs (1X2 le plus probable) |     7145 |       1      |     0.5283 |               0.5326 |              0.5268 |                           0.0016 |                0.4998 |     0.6583 |  0.2333 |                      73.9663 |

### test final T 2025-26 — mode « compromis »

|                                        |   matchs |   couverture |   réussite |   p moyenne annoncée |   référence moyenne |   succès en plus de la référence |   borne basse moyenne |   log loss |   Brier |   information publiée (bits) |
|:---------------------------------------|---------:|-------------:|-----------:|---------------------:|--------------------:|---------------------------------:|----------------------:|-----------:|--------:|-----------------------------:|
| retenue                                |     1026 |       0.5856 |     0.881  |               0.8667 |              0.7306 |                           0.1503 |                0.8549 |     0.3547 |  0.103  |                      91.0512 |
| prudente                               |      303 |       0.1729 |     0.755  |               0.7775 |              0.685  |                           0.07   |                0.7648 |     0.557  |  0.185  |                       9.5235 |
| abstention                             |      423 |       0.2414 |     0.9149 |               0.9211 |              0.9323 |                          -0.0174 |                0.9137 |     0.2913 |  0.0779 |                       0      |
| tous les matchs (1X2 le plus probable) |     1752 |       1      |     0.5183 |               0.5246 |              0.5184 |                          -0.0001 |                0.4919 |     0.6574 |  0.2329 |                      18.5454 |

### test final T 2025-26 — mode « probable »

|                                        |   matchs |   couverture |   réussite |   p moyenne annoncée |   référence moyenne |   succès en plus de la référence |   borne basse moyenne |   log loss |   Brier |   information publiée (bits) |
|:---------------------------------------|---------:|-------------:|-----------:|---------------------:|--------------------:|---------------------------------:|----------------------:|-----------:|--------:|-----------------------------:|
| retenue                                |     1026 |       0.5856 |     0.8859 |               0.869  |              0.7452 |                           0.1407 |                0.8574 |     0.3427 |  0.0991 |                      76.1931 |
| prudente                               |      303 |       0.1729 |     0.7517 |               0.782  |              0.6917 |                           0.06   |                0.7702 |     0.5618 |  0.1871 |                       9.0538 |
| abstention                             |      423 |       0.2414 |     0.9149 |               0.9211 |              0.9323 |                          -0.0174 |                0.9137 |     0.2913 |  0.0779 |                       0      |
| tous les matchs (1X2 le plus probable) |     1752 |       1      |     0.5183 |               0.5246 |              0.5184 |                          -0.0001 |                0.4919 |     0.6574 |  0.2329 |                      18.5454 |

Réussite des abstentions = réussite qu'aurait eue la sélection la plus informative si on l'avait retenue (pour vérifier que l'abstention écarte bien des cas moins fiables).

## 7. Test final : sélections retenues par famille de marché et par championnat

| famille          |   sélections |   réussite |   p_moyenne |
|:-----------------|-------------:|-----------:|------------:|
| Buts             |          163 |     0.8282 |      0.8196 |
| Double chance    |            5 |     0.6    |      0.8306 |
| Remboursé si nul |            1 |     1      |      0.8239 |
| Équipe marque    |          856 |     0.8925 |      0.8759 |
| ligue   |   sélections |   réussite |   p_moyenne |
|:--------|-------------:|-----------:|------------:|
| D1      |          213 |     0.9296 |      0.8803 |
| E0      |          202 |     0.8911 |      0.8613 |
| F1      |          169 |     0.8343 |      0.8774 |
| I1      |          212 |     0.8538 |      0.8508 |
| SP1     |          229 |     0.8865 |      0.8656 |
| p_meta     |    n |   annoncé |   observé |
|:-----------|-----:|----------:|----------:|
| (0.0, 0.1] |  299 |     0.068 |     0.074 |
| (0.1, 0.2] | 1069 |     0.156 |     0.154 |
| (0.2, 0.3] | 2294 |     0.254 |     0.268 |
| (0.3, 0.4] | 2259 |     0.351 |     0.345 |
| (0.4, 0.5] | 4240 |     0.455 |     0.46  |
| (0.5, 0.6] | 4659 |     0.547 |     0.542 |
| (0.6, 0.7] | 3932 |     0.653 |     0.66  |
| (0.7, 0.8] | 5265 |     0.749 |     0.739 |
| (0.8, 0.9] | 2838 |     0.845 |     0.846 |
| (0.9, 1.0] | 2037 |     0.935 |     0.94  |

## 8. Valeur statistique (secondaire, cotes moyennes du marché, pas de cotes de clôture)


Le rendement n'est pas un objectif : les cotes moyennes incluent la marge du bookmaker, et aucune cote de clôture n'est disponible.
