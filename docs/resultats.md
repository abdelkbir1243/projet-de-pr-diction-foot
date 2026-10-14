# Résultats

Tous les chiffres ci-dessous sont reproductibles avec `python scripts/reproduire.py`. Les tables CSV se trouvent dans `results/tables/` et les figures dans `results/figures/`.
Log loss : plus bas = mieux. Δ exprimé en ×10⁻³. IC = intervalle de confiance à 95 % obtenu par bootstrap apparié.

## 0. Comparaison officielle sur les mêmes matchs (8 896 matchs, 2021/22 → 2025/26)

Produite par `python scripts/comparaison_commune.py` (tables `results/tables/comparaison_commune_*.csv`). Tous les modèles utilisent
les variables construites avec la deuxième division (promus inclus) et sont notés sur les mêmes 8 896 matchs.

| Modèle | Log loss | RPS | Brier | ECE | Bon résultat |
|---|---|---|---|---|---|
| Fréquences | 1,0736 | 0,2300 | 0,6497 | 0,010 | 43,5 % |
| Elo seul | 0,9852 | 0,1998 | 0,5874 | 0,012 | 52,5 % |
| v3 | 0,9816 | 0,1988 | 0,5849 | 0,013 | 53,0 % |
| v4 | 0,9812 | 0,1987 | 0,5844 | 0,012 | 52,7 % |
| **v5** | **0,9810** | **0,1987** | **0,5844** | **0,011** | 52,6 % |
| Cotes | 0,9710 | 0,1954 | 0,5775 | 0,015 | 53,7 % |

v5 − Elo seul : −4,20 ×10⁻³ [−6,55 ; −1,78] · v5 − v4 : −0,21 [−1,07 ; +0,57] · v4 − v3 : −0,40 [−1,55 ; +0,77] · v5 − Cotes : +9,98 [+7,27 ; +12,81].

**Statut** : évaluation rétrospective. Les variables de v5 ont été étudiées sur 2010-2025 (§11), qui recoupe 2021-2026 ;
l'évaluation prospective est le journal 2026/27 (prédictions figées avant le coup d'envoi). Les sections suivantes conservent
l'historique du projet (8 821 matchs avant l'ajout des promus) et ne doivent pas être mélangées avec ce tableau.

## 1. Test 1X2 historique de v3/v4, 2021/22 → 2025/26 (8 821 matchs, walk-forward, avant l'ajout des promus)

| Modèle | Log loss | RPS | Brier | ECE | Bon résultat | Skill score |
|---|---|---|---|---|---|---|
| Fréquences | 1,0737 | 0,2300 | 0,6497 | 0,010 | 43,5 % | 0 % |
| Elo seul | 0,9864 | 0,2001 | 0,5882 | 0,013 | 52,4 % | 8,1 % |
| v3 | 0,9823 | 0,1990 | 0,5854 | 0,013 | 52,9 % | 8,5 % |
| **v4** | **0,9818** | **0,1989** | **0,5849** | **0,011** | 52,6 % | **8,6 %** |
| Cotes | 0,9722 | 0,1957 | 0,5783 | 0,015 | 53,7 % | 9,5 % |

| Comparaison | Δ log loss | IC 95 % | Conclusion |
|---|---|---|---|
| v4 − v3 (1X2) | −0,52 | [−1,70 ; +0,69] | non significatif |
| v4 − Elo seul | −4,55 | [−6,83 ; −2,21] | **significatif** |
| v4 − cotes | +9,64 | [+6,76 ; +12,32] | le marché reste meilleur |
| v4 − v3 (score exact) | −5,17 | [−7,53 ; −2,76] | **significatif** |
| v4 − v3 (over 2,5) | −4,24 | [−6,00 ; −2,48] | **significatif** |

## 2. Marchés de buts (même test)

| | LL score exact | LL over 2,5 | LL BTTS | Buts prévus / match |
|---|---|---|---|---|
| v3 | 2,9119 | 0,6802 | 0,6857 | 2,805 |
| **v4** | **2,9067** | **0,6759** | **0,6839** | 2,808 |
| Cotes over/under | — | 0,6717 | — | — |
| Réel | — | — | — | 2,808 |

La calibration de l'over 2,5 est bonne. Par quintile de probabilité annoncée : 42 % annoncé → 41 % observé, 48 → 48, 52 → 53, 56 → 59, 65 → 66.

## 3. Stabilité par ligue et par saison (log loss 1X2)

| Ligue | Elo seul | v3 | v4 | Cotes |
|---|---|---|---|---|
| Bundesliga | 0,9906 | 0,9866 | 0,9862 | 0,9763 |
| Liga | 0,9828 | 0,9787 | 0,9770 | 0,9675 |
| Ligue 1 | 1,0006 | 0,9952 | 0,9942 | 0,9837 |
| Premier League | 0,9794 | 0,9746 | 0,9737 | 0,9606 |
| Serie A | 0,9809 | 0,9788 | 0,9801 | 0,9750 |

| Saison | Elo seul | v3 | v4 | Cotes |
|---|---|---|---|---|
| 2021/22 | 0,9903 | 0,9886 | 0,9862 | 0,9778 |
| 2022/23 | 0,9867 | 0,9832 | 0,9878 | 0,9805 |
| 2023/24 | 0,9719 | 0,9679 | 0,9664 | 0,9567 |
| 2024/25 | 0,9855 | 0,9806 | 0,9782 | 0,9650 |
| 2025/26 | 0,9972 | 0,9911 | 0,9902 | 0,9802 |

v4 est meilleur que v3 dans 4 ligues sur 5 et 4 saisons sur 5. Contrairement à une idée reçue, la Ligue 1 et la Liga ne sont pas plus prévisibles que la Premier League.

## 4. Laboratoire : saison 2025/26

**Modèle figé au 1er juillet 2025** (1 737 matchs) :

| | Log loss | RPS | Bon résultat |
|---|---|---|---|
| Elo seul | 0,9972 | 0,2035 | 51,2 % |
| v3 | 0,9911 | 0,2015 | 51,5 % |
| v4 | 0,9902 | 0,2011 | 51,1 % |
| Cotes | 0,9802 | 0,1980 | 53,3 % |

**Saison rejouée semaine par semaine** (37 semaines, ré-entraînement chaque lundi) :

| Indicateur | Valeur |
|---|---|
| Log loss avec ré-entraînement hebdomadaire | 0,9906 |
| Log loss du modèle figé | 0,9902 |
| Gain du ré-entraînement | +0,40 ×10⁻³, IC [−0,23 ; +1,01] : nul |
| Écart avec les cotes | +10,3 ×10⁻³, IC [+3,6 ; +17,1] |
| Semaines où v4 bat les cotes | 16 / 37 (43 %) |

Conclusion : les ratings se mettent à jour après chaque match. Ré-estimer les coefficients chaque semaine n'apporte rien, un ré-entraînement par saison suffit.

## 5. Efficience du marché : stratégies simulées (test 2021-2026)

Rendement moyen par mise de 1 :

| Stratégie | Paris | Gagnés | Rendement | IC 95 % |
|---|---|---|---|---|
| Value v4 contre la cote moyenne, seuil 0 % | 9 209 | 31,7 % | −5,8 % | [−8,9 ; −2,3] |
| Value v4 contre la cote moyenne, seuil 5 % | 5 512 | 29,1 % | −8,4 % | [−12,7 ; −4,1] |
| Value v4 contre la cote moyenne, seuil 10 % | 3 099 | 26,6 % | −10,7 % | [−16,7 ; −4,5] |
| Value v4 contre la cote moyenne, seuil 20 % | 1 109 | 19,8 % | −21,1 % | [−31,6 ; −11,0] |
| Value v4 contre la meilleure cote, seuil 0 % | 13 011 | 31,3 % | −2,0 % | [−5,0 ; +1,2] |
| Toujours le favori | 8 821 | 53,7 % | −2,2 % | [−4,2 ; −0,3] |
| Toujours le nul | 8 821 | 25,4 % | −2,5 % | [−6,0 ; +1,1] |
| Toujours l'outsider | 8 821 | 20,7 % | −10,4 % | [−14,4 ; −6,3] |

Expérience complémentaire : un modèle v4 qui reçoit aussi les cotes en entrée atteint une log loss de 0,9713, contre 0,9722 pour les cotes seules. L'écart est non significatif (IC [−2,2 ; +0,4] ×10⁻³). Le meilleur rendement simulé avec ce modèle est de +2,6 %, IC [−6,3 % ; +11,5 %] : **aucune stratégie n'est démontrée gagnante**. Le seul biais net est le biais favori-outsider.

## 6. Nombre de variables et surapprentissage (test 2021-2026)

| Variables | Méthode | LL sur l'entraînement | LL sur le test |
|---|---|---|---|
| Elo seul (2) | logit | 0,981 | 0,9864 |
| **v4 (12)** | logit | 0,975 | **0,9819** |
| v4 + forme, tirs, corners, repos (38) | logit régularisé | 0,972 | 0,9813 |
| v4 + forme, tirs, corners, repos (38) | LightGBM | 0,949 | 0,9841 |
| Tout (112) | logit | 0,966 | 0,9840 |
| Tout (112) | logit régularisé | 0,969 | 0,9835 |
| Tout (112) | LightGBM | 0,959 | 0,9847 |

Quand on ajoute des variables, l'erreur sur l'entraînement baisse mais l'erreur sur le test remonte : c'est la signature du surapprentissage. Les variables supplémentaires sont redondantes avec les ratings. Pour progresser, il faudrait de l'**information nouvelle** (compositions, blessures, vrais xG), pas plus de paramètres.

## 7. Méthodes des guides de paris confrontées aux données (2005-2025)

| Affirmation | Mesure | Verdict |
|---|---|---|
| « Surebet français » gagne 8 fois sur 10 | réussite 79,4 %, rendement −4,3 % | vrai en fréquence, perdant en moyenne |
| Toute cote domicile > 2,17 est une value | victoire à domicile 30,3 %, rendement −6,4 % | faux |
| Poisson « attaque × défense » (Kit foot) | log loss 1,013 contre 0,983 pour le modèle | utile mais dépassé ; son étape 1 est intégrée |
| BTTS : Bundesliga 56,7 %, Ligue 1 48,7 % | 57,1 % et 50,1 % | confirmé |
| « BTTS non » rapporte 37 % de plus que « moins de 2,5 » | 47,6 % contre 48,8 % | faux |
| BTTS plus faible à 15 h en Premier League | à cotes égales, p = 0,32 | non confirmé |
| 70 % des matchs ont un but en 1re mi-temps | 70,0 % | confirmé, marché ajouté |
| « Fin de série » après deux 0-0 à la pause | 67,5 % contre 70,0 %, p = 0,33 | faux (sophisme du joueur) |
| Écarter les fins de saison | skill score de 7,1 % en mai contre 8,9 % le reste de l'année | plutôt confirmé : alerte ajoutée |
| Stratégie anti-favoris | favori −2,8 %, outsider −11,3 % | faux (biais favori-outsider) |

## 8. Historique des versions (log loss sur le test 2021-2026)

| Version | Contenu | Log loss 1X2 |
|---|---|---|
| v1 | Logit sur ΔElo + ΔQ | 0,9844 |
| v2 | Ensemble XGBoost, LightGBM, CatBoost et logit, avec 100+ variables | ≈ 0,984-0,986 (plateau) |
| v3 | + pi-ratings, ouverture, \|ΔElo\|, ligue, pondération temporelle, marchés dérivés | 0,9823 |
| v4 | + ratings de buts GAS ; correction de la fuite sur c_L | 0,9818 (buts : −5 ×10⁻³) |
| v4.3 | forme des promus calculée sur leurs matchs de 2e division (8 897 matchs testés au lieu de 8 821) | 0,9812 |
| **v5** | + enjeu de fin de saison (course au titre, maintien, sans enjeu) | **0,9810** |

## 9. Corners et cartons (test 2021-2026, 8 822 matchs)

| Statistique | Moyenne réelle | LL « moyenne de la ligue » | LL modèle | Δ ×10⁻³ | IC 95 % | Corrélation prévu / réel |
|---|---|---|---|---|---|---|
| Corners (total) | 9,68 | 2,6122 | 2,6074 | −4,8 | [−7,2 ; −2,3] | 0,14 |
| Cartons jaunes (total) | 4,10 | 2,1447 | 2,1239 | −20,8 | [−25,0 ; −16,3] | 0,28 |
| Cartons rouges (total) | 0,19 | 0,5220 | 0,5199 | −2,0 | [−3,3 ; −0,8] | 0,13 |

Calibration par quintile (probabilité annoncée → fréquence observée) :
- **Corners plus de 9,5** : 42 → 43 %, 46 → 47 %, 49 → 50 %, 53 → 52 %, 60 → 58 %.
- **Jaunes plus de 4,5** : 23 → 25 %, 31 → 34 %, 37 → 38 %, 43 → 45 %, 55 → 56 %. Légère sous-estimation, d'environ 2 points.
- **Au moins un rouge** : 11 → 10 %, 14 → 14 %, 17 → 17 %, 19 → 20 %, 24 → 24 %.

Lecture : les modèles battent nettement la simple moyenne de la ligue, mais ces statistiques restent très incertaines. Pour comparaison, la corrélation prévu/réel vaut 0,21 pour le total de buts et 0,45 pour l'écart de buts. Les corners (0,14) sont donc un peu moins prévisibles que le total de buts, les jaunes (0,28) un peu plus. L'arbitre, facteur majeur des cartons, n'est pas dans les données.

## 10. Fiabilité des paliers de risque (test 2021-2026)

On a testé 30 marchés sur chacun des 8 822 matchs, soit 264 660 décisions. Chaque prédiction a été faite par un modèle entraîné sur les saisons antérieures uniquement.

| Palier | Décisions | Probabilité annoncée | Taux réalisé | Rendement aux cotes réelles* |
|---|---|---|---|---|
| 1 · très faible (≥ 80 %) | 20 726 | 85,1 % | 85,3 % | −1,2 % |
| 2 · faible (65-80 %) | 51 321 | 72,2 % | 72,2 % | −3,4 % |
| 3 · modéré (50-65 %) | 68 683 | 57,0 % | 56,9 % | −2,9 % |
| 4 · élevé (35-50 %) | 65 080 | 43,2 % | 43,2 % | −6,2 % |
| 5 · très élevé (< 35 %) | 58 850 | 24,5 % | 24,7 % | −7,6 % |

\* Rendement calculé uniquement sur les marchés dont la cote réelle figure dans les données (1X2, plus/moins de 2,5 buts).

- **Le classement par risque est remarquablement bien calibré** : dans chaque palier, la probabilité annoncée et la fréquence observée diffèrent de moins de 0,3 point.
- **La décision prudente** (l'issue la plus probable de chaque match) annonçait 85,4 % en moyenne et s'est réalisée 85,8 % du temps.
- **Moins de risque ne veut pas dire plus de gain.** Aux cotes réelles, tous les paliers ont un rendement négatif. Le moins mauvais est le palier très faible (−1,2 %), cohérent avec le biais favori-outsider : les issues les plus probables sont les moins taxées par la marge.


## 11. Modèle v5 : contexte des matchs et combinaison avec les cotes

Questions testées : le repos, l'enchaînement des matchs, la phase de saison (mercato), le statut de promu ou de champion en titre
et la motivation au classement améliorent-ils les prédictions ? Toutes les variables utilisent le classement **de la veille** du
match (test de non-fuite étendu : `tests/test_fuite.py`, `tests/test_contexte.py`).

**a. Effet sur les résidus du modèle** (points obtenus − points attendus par v4, matchs 2010-2025 hors échantillon, IC 95 % bootstrap)

| Situation | Matchs | Écart (pts/match) | IC 95 % |
|---|---|---|---|
| Repos ≤ 3 jours | 5 421 | +0,016 | [−0,016 ; +0,049] |
| Promu | 7 605 | +0,004 | [−0,022 ; +0,028] |
| Promu, 6 premiers matchs | 923 | +0,038 | [−0,035 ; +0,113] |
| Champion en titre | 2 931 | −0,028 | [−0,068 ; +0,014] |
| Début de saison (< 6 matchs) | 8 812 | −0,005 | [−0,029 ; +0,019] |
| **Course au titre** (8 dernières journées) | 560 | **+0,138** | [+0,044 ; +0,224] |
| **Lutte pour le maintien** | 3 602 | **+0,078** | [+0,040 ; +0,118] |
| **Sans enjeu** | 4 769 | **−0,057** | [−0,091 ; −0,021] |
| **Sans enjeu face à une équipe avec enjeu** | 2 638 | **−0,107** | [−0,155 ; −0,059] |

Le repos, le statut et la phase de saison sont déjà absorbés par l'Elo et la forme. Seul l'**enjeu de fin de saison** laisse un
effet significatif : c'est la seule variable ajoutée au modèle (v5). Les autres restent affichées dans l'interface, à titre informatif.

**b. Évaluation rétrospective 2021-2026 (8 897 matchs ; voir §0 pour la comparaison officielle sur 8 896 matchs communs)**

| | Log loss | RPS | Brier | ECE | Bon résultat |
|---|---|---|---|---|---|
| v4 (mêmes données) | 0,9812 | 0,1987 | 0,5845 | 0,0116 | 52,7 % |
| **v5** | **0,9810** | 0,1987 | **0,5844** | **0,0113** | 52,6 % |
| Cotes (référence) | 0,9710 | 0,1954 | 0,5775 | 0,0153 | 53,7 % |

Gain v5 − v4 : −0,21 ×10⁻³, IC [−0,97 ; +0,58] (non significatif sur l'ensemble, l'effet ne concerne que 1 780 matchs de fin de saison).
Sur 2015-2026, les matchs de fin de saison gagnent −1,6 ×10⁻³ en 1X2 et −2,6 ×10⁻³ sur l'over 2,5. Conclusion honnête : la v5 est
légèrement mieux calibrée, mais le gain reste dans le bruit statistique.

**c. Combinaison modèle + cotes** (moyenne logarithmique, poids appris sur les saisons précédentes, 2015-2026, 19 533 matchs)

Le poids optimal du modèle est de 0 à 0,02 chaque saison : **les cotes contiennent déjà toute l'information du modèle**.
La plateforme affiche donc les écarts modèle / marché comme des questions à étudier, jamais comme des opportunités.


## 12. Degré de confiance et analyse jour par jour

Recalculé à chaque publication : backtest walk-forward des 5 dernières saisons **et de la saison en cours** (chaque saison
prédite par un modèle entraîné sur les précédentes), soit ≈ 9 000 matchs et 270 000 issues sur 30 marchés (`footpred/confiance.py`).

**a. Qu'est-ce qui rend une prédiction moins fiable ?** (2012-2026, 24 879 matchs hors échantillon, favori du modèle)

| Situation | Matchs | Favori annoncé | Favori réalisé | ECE |
|---|---|---|---|---|
| Accord avec les cotes (écart < 5 pts) | 14 513 | 53,8 % | 54,4 % | 0,009 |
| Désaccord modéré (5-10 pts) | 7 994 | 52,5 % | 51,9 % | 0,016 |
| Désaccord marqué (10-15 pts) | 1 930 | 53,2 % | 49,8 % | 0,037 |
| Désaccord très marqué (≥ 15 pts) | 440 | 53,5 % | 46,4 % | 0,097 |
| Moins de 3 matchs joués dans la saison | 1 901 | 53,1 % | 52,4 % | 0,028 |
| 15 matchs joués ou plus | 14 848 | 53,5 % | 53,3 % | 0,012 |
| Un promu dans le match | 6 282 | 53,7 % | 53,7 % | 0,015 |

Le désaccord avec les cotes est de loin le meilleur signal : quand le modèle s'écarte du marché, il est trop confiant.
Le début de saison dégrade la calibration ; le statut de promu n'a pas d'effet.

**b. Niveaux publiés** (2021-2026) : A = accord avec les cotes et saison installée ; B = désaccord modéré ou moins de 4 matchs joués ;
C = désaccord ≥ 10 points.

| Niveau | Part | Favori annoncé | Favori réalisé (IC 95 %) | Log loss |
|---|---|---|---|---|
| A · élevé | 54 % | 53,3 % | 53,4 % (52,0-54,8) | 0,972 |
| B · moyen | 38 % | 52,2 % | 52,2 % (50,5-53,9) | 0,981 |
| C · faible | 8 % | 52,7 % | 49,8 % (46,2-53,4) | 1,036 |

**c. Calibration de chaque statistique** : écart moyen entre probabilité annoncée et fréquence observée, par classes de 5 points :
buts 0,6 pt, corners 0,4 pt, cartons 0,8 pt, résultat et double chance 0,8 pt. Chaque marché affiché sur un match indique la
fréquence réalisée de sa classe, avec son intervalle de Wilson.

**d. Journée** : pour chaque date, le site additionne les lois des matchs (convolution des lois du nombre de buts et des corners,
loi de Poisson-binomiale pour les victoires, nuls et favoris) et publie des intervalles à 80 %. Une fois la journée jouée, il
affiche le résultat réel en regard ; la page Performance IA montre les courbes cumulées attendu / observé des 60 dernières dates.


## 13. Données d'événements : test de Hassard & Kerr (2024)

L'article prédit les matchs 2015/16 des grands championnats avec des variables tirées des événements StatsBomb (possession,
passes et conduites par zone, field tilt, xG, expected threat xT) et annonce 61 à 66 % de bonnes prédictions (SVM, Random Forest,
XGBoost). Nous avons refait l'étude avec les mêmes données (`scripts/sb_agg.py`, `scripts/etude_statsbomb.py`) : 1 551 matchs
(la Bundesliga n'a que 34 matchs dans les données ouvertes), 20 variables par équipe, grille xT 12 × 8 estimée par itération de valeur.
En A (reproduction, variables du match lui-même), la grille xT est estimée sur toute la saison comme dans l'article. En B et C,
**sans fuite** : la grille utilisée pour un match n'est estimée que sur les matchs joués avant sa date (60 matchs minimum).

**A. Reproduction : variables calculées sur le match lui-même, découpage aléatoire 80/20**

| Modèle | Bon résultat | Log loss |
|---|---|---|
| SVM linéaire | 65,3 % | 0,807 |
| XGBoost (1 000 arbres, taux 0,01, profondeur 3, réglages de l'article) | 65,3 % | 0,778 |
| Régression logistique | 64,6 % | 0,764 |
| Random Forest | 62,4 % | 0,831 |

Les chiffres de l'article sont reproduits. Mais ces variables (xG, tirs cadrés, possession **du match**) ne sont connues qu'après
le coup d'envoi : le modèle **décrit** le match, il ne le **prédit** pas. De plus, le découpage aléatoire mélange passé et futur.

**B. Prédiction réelle avant le match** (moyenne des matchs précédents de la saison, comme la section V de l'article ;
chaque semaine prédite par un modèle entraîné sur les semaines précédentes ; 1 112 matchs communs)

| Modèle | Bon résultat | Log loss | Brier |
|---|---|---|---|
| Régression logistique, variables d'événements | 49,9 % | 1,037 | 0,619 |
| XGBoost, variables d'événements | 47,0 % | 1,078 | 0,641 |
| Régression logistique, Elo seul | 51,1 % | 0,987 | 0,588 |
| **Modèle v5** (entraîné sur les saisons antérieures) | **52,2 %** | **0,974** | **0,580** |
| Cotes des bookmakers | 52,5 % | 0,970 | 0,578 |

Dès que l'on se place avant le match, les variables d'événements seules font moins bien que l'Elo : une demi-saison de moyennes
est trop courte et trop bruitée pour estimer la force d'une équipe.

**C. Valeur ajoutée au modèle v5** (empilement : log-rapports de v5 + différences des moyennes d'avant-match, même protocole)

| Ajout | Écart de log loss (×10⁻³) | IC 95 % |
|---|---|---|
| xG | +0,3 | [−3,0 ; +3,7] |
| xT | −0,0 | [−4,3 ; +4,2] |
| Field tilt | +0,1 | [−3,1 ; +3,2] |
| xG, xT, field tilt, tirs, possession | +6,8 | [−0,4 ; +13,4] |

Aucun gain (chiffres avec la grille xT sans fuite ; la version précédente, grille estimée sur toute la saison, donnait la même
conclusion : xT +0,5 [−2,8 ; +3,7]) : sur une saison, ces variables n'apportent pas d'information au-delà de l'Elo, des pi-ratings et des xG approchés du
modèle. Les corrélations le confirment : les tirs cadrés et les xG **du match** sont corrélés à la victoire à domicile (0,38 et 0,35),
leurs moyennes **d'avant-match** beaucoup moins (0,21 et 0,20) ; la possession seule l'est très peu (0,03 dans le match), comme l'article.

**Conclusion.** L'article est utile pour ses variables (xT, field tilt, zones) et montre bien que la qualité des occasions compte plus
que la possession. Mais ses 64 % mesurent une explication du résultat, pas une prédiction : sans les données du match, on retombe
sous les 53 % atteints par les bookmakers. Limites de notre test : une seule saison gratuite (2015/16), 1 112 matchs, donc des
intervalles larges ; les données d'événements ne sont pas disponibles en continu gratuitement, ce qui empêche de les utiliser en
production.


## 14. Deux autres articles confrontés à nos données

**a. Ren & Susnjak (2022) : « Kelly Index » et matchs faciles / difficiles.** L'article classe 1 140 matchs de Premier League
(2019-2021) selon l'écart entre les cotes de six bookmakers et la cote moyenne : type 1 (plusieurs bookmakers au-dessus), type 2,
type 3 (aucun). Il annonce 70 % de bons résultats sur le type 1 et un rendement de +17 % en ne pariant que sur le type 1 quand le
modèle est confiant à plus de 70 %.

Test sur nos données (24 877 matchs des 5 ligues, 2012-2026, hors échantillon) avec un indicateur équivalent : l'écart entre la
meilleure cote et la cote moyenne (seules ces deux cotes sont disponibles).

| Dispersion des cotes | Matchs | Favori annoncé par le marché | Favori réalisé | Log loss modèle − marché |
|---|---|---|---|---|
| Faible | 8 298 | 46,8 % | 46,4 % | +10,1 ×10⁻³ |
| Moyenne | 8 332 | 50,8 % | 51,7 % | +11,4 ×10⁻³ |
| Forte | 8 247 | 62,6 % | 63,8 % | +10,1 ×10⁻³ |

La dispersion trie surtout les matchs **selon la netteté du favori** : les matchs « faciles » sont ceux où un favori écrasant existe.
À probabilité du favori égale, elle n'apporte presque rien (régression logistique : coefficient de la dispersion p = 0,14), et
l'écart entre le modèle et le marché est le même dans les trois groupes. Les 70 % du type 1 s'expliquent donc par la composition
du groupe, pas par un gain de prédiction. Le rendement de +17 % repose sur un seul seuil choisi parmi plusieurs, sur quelques dizaines
de matchs : c'est un cas typique de sur-ajustement. Sur nos 264 660 décisions testées (§10), aucun palier n'est rentable.
Idée retenue : séparer les matchs par niveau de difficulté est utile **pour mesurer la confiance**, ce que fait déjà notre degré
de confiance (§12), mais pas pour « battre » le marché.

**b. Sallis, Georgoulas & Tsoulos (2026)** : 225 474 matchs, découpage chronologique, log loss, Brier, RPS, IC bootstrap, et
comparaison systématique avec les cotes sans marge. Leurs conclusions rejoignent exactement les nôtres :

| | Sallis et al. (2026), 583 compétitions | Ce projet, 5 grands championnats |
|---|---|---|
| Modèles sans les cotes | 48,0 % · log loss 1,029 | 52,6 % · log loss 0,981 |
| Cotes sans marge | 51,9 % · log loss 0,984 | 53,7 % · log loss 0,971 |
| Fréquences seules | 43,5 % · log loss 1,074 | 43,5 % · log loss 1,074 |
| Choix de l'algorithme | six algorithmes à moins de 0,1 point | ML complexe ≈ logit (§6) |
| Modèle + cotes | jamais meilleur que les cotes seules | poids optimal du modèle ≈ 0 (§11) |

Ils montrent aussi que les « 65 % » obtenus en un-contre-tous (victoire domicile contre le reste) ne sont pas comparables à une
précision sur trois issues, et que le nul n'est presque jamais l'issue la plus probable (0,5 % des matchs pour le marché) : c'est
une propriété du football, pas un défaut des modèles.

Leur méthode pour retirer la marge (méthode de la puissance, exposant trouvé par Newton-Raphson) a été comparée à la nôtre :

| Méthode (24 877 matchs) | Log loss | Brier | ECE |
|---|---|---|---|
| Proportionnelle | 0,96612 | 0,57385 | 0,0115 |
| Puissance (Sallis et al.) | 0,96555 | 0,57352 | 0,0077 |
| Shin (utilisée par le site) | 0,96565 | 0,57358 | 0,0083 |

Puissance et Shin sont équivalentes (écart −0,11 ×10⁻³, IC [−0,23 ; +0,02]) et toutes deux meilleures que la normalisation
proportionnelle (écart +0,47 ×10⁻³, IC [+0,23 ; +0,71]). La méthode de Shin est conservée.

Script : `scripts/etude_articles_2026.py`.


## 15. Coupes d'Europe : modèle Elo et fatigue

**Données** : openfootball/champions-league (GitHub, gratuit) : Ligue des champions depuis 2011/12, Ligue Europa depuis 2020/21,
Conference League depuis 2021/22, soit 3 390 matchs. Le score retenu est celui des 90 minutes (prolongations et tirs au but exclus).
157 clubs sont rattachés au dataset (Elo ClubElo, calibré pour toute l'Europe) ; les 67 autres (Ukraine, Croatie, Serbie,
Chypre, Kazakhstan…) reçoivent un Elo **estimé** sur leurs seuls matchs européens, en partant de la moyenne des clubs déjà vus de
leur pays. Les variables propres à un championnat (pi-ratings, ratings de buts, xG approchés) ne sont pas comparables d'un pays à
l'autre et ne sont pas utilisées.

**Évaluation hors échantillon** (2014/15 → 2025/26, chaque saison prédite par un modèle entraîné sur les précédentes, 3 013 matchs)

| Variables | Log loss | Bon résultat | ECE |
|---|---|---|---|
| Fréquences seules | 1,047 | — | — |
| **Écart d'Elo seul (retenu)** | **0,944** | 56,2 % | 0,024 |
| + \|écart\|, terrain neutre | 0,947 | 56,2 % | 0,019 |
| + phase à élimination, Elo estimé | 0,949 | 55,9 % | 0,018 |

Le modèle le plus simple est le meilleur (skill score ≈ 10 %, comparable aux championnats). Par compétition : Ligue des champions
0,914 (58,6 %), Ligue Europa 0,965 (55,6 %), Conference League 0,999 (50,5 %) : plus le niveau est hétérogène et les clubs
inconnus nombreux, moins la prédiction est précise. Quand les deux clubs ont un Elo estimé, la log loss monte à 1,045 :
ces matchs reçoivent le niveau de confiance C, les autres B (jamais A : pas de cotes gratuites pour vérifier l'accord avec le
marché, pas de corners ni de cartons).

**Fatigue : un match européen pèse-t-il sur le match de championnat suivant ?** (`scripts/etude_fatigue_europe.py`, 2012-2026,
résidu = points obtenus − points attendus par le modèle hors échantillon)

| Situation | Matchs | Écart (pts/match) | IC 95 % |
|---|---|---|---|
| Match européen 2-3 jours avant | 1 372 | −0,001 | [−0,061 ; +0,060] |
| Match européen 4-5 jours avant | 1 644 | **−0,080** | [−0,138 ; −0,020] |
| Club européen sans match dans les 7 jours | 15 223 | +0,017 | [−0,001 ; +0,037] |

Effet faible et fragile : significatif seulement à 4-5 jours, nul à 2-3 jours, et les matchs de Ligue Europa ne sont connus
qu'à partir de 2020. Il n'est pas ajouté au modèle ; les matchs européens sont en revanche désormais comptés dans le repos
affiché sur chaque match.
