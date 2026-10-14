# Méthodologie du modèle v5 (package 5.4)

## 1. Données

- **Source** : dataset public *Club-Football-Match-Data* (xgabora), environ 50 Mo et 230 000 matchs de 2000 à aujourd'hui. Il est construit à partir de football-data.co.uk et de ClubElo.
- **Colonnes utilisées** :
  - date, équipes, division ;
  - buts à la mi-temps et en fin de match ;
  - tirs cadrés ;
  - Elo d'avant-match (ClubElo) ;
  - cotes 1X2 et over/under, qui servent **uniquement** de référence d'évaluation.
- **Périmètre de modélisation** : Premier League (E0), Liga (SP1), Serie A (I1), Bundesliga (D1) et Ligue 1 (F1), à partir de la saison 2005/06. Les ratings sont calculés sur **toutes** les ligues du dataset, pour que les promus arrivent déjà avec une note.
- **Saison** : de juillet à juin, notée par son année de début (2025 = 2025/26).

## 2. Ratings dynamiques (mis à jour après chaque match)

### 2.1 ClubElo

Pris tel quel dans le dataset. Variable : ΔElo = (Elo_dom − Elo_ext)/100, et |ΔElo|, car le nul est plus probable quand les forces sont proches.

### 2.2 pi-ratings (Constantinou & Fenton 2013)

Chaque équipe a une note à domicile R_H et une note à l'extérieur R_A. L'écart de buts attendu vaut ê = ψ(R_H,dom) − ψ(R_A,ext), avec ψ(r) = sign(r)·(10^{|r|/3} − 1).

Après le match :
- erreur e = (buts_dom − buts_ext) − ê ;
- erreur amortie s = sign(e)·3·log10(1 + |e|) ;
- mises à jour R_H,dom += λ·s, R_A,ext −= λ·s, et les notes croisées bougent de γ fois ce changement.

Paramètres : λ = 0,035 et γ = 0,7, ceux de l'article.

Variables :
- pi_diff = R_H,dom − R_A,ext ;
- pi_diff_avg = moyenne(R_dom) − moyenne(R_ext).

### 2.3 Ratings de buts à score GAS (Koopman & Lit 2019), apport principal de la v4

Pour un match de la ligue L :

```
log λ_dom = μ_L + h_L + att_dom − déf_ext
log λ_ext = μ_L − h_L + att_ext − déf_dom
```

Après le match, mise à jour par le gradient de la log-vraisemblance de Poisson (le « score ») :

```
att_dom ← att_dom + η (buts_dom − λ_dom)      déf_ext ← déf_ext − η (buts_dom − λ_dom)
att_ext ← att_ext + η (buts_ext − λ_ext)      déf_dom ← déf_dom − η (buts_ext − λ_ext)
μ_L, h_L mis à jour au pas η_L
```

- Quand une équipe change de division (promotion ou relégation), att et déf sont multipliés par 0,5.
- **Réglage** : η = 0,0125, η_L = 0,0001, rétrécissement 0,5. Ces valeurs maximisent la vraisemblance de Poisson des buts sur **2006-2015 uniquement**, donc avant la sélection et le test.
- Variables : g_lh = log λ_dom et g_la = log λ_ext, calculés avant le match.

## 3. Autres variables d'avant-match

- **xG approché** = c_L,s × tirs cadrés. c_L,s est le nombre de buts par tir cadré de la ligue, estimé sur les **saisons antérieures** (0,25 en Premier League, environ 0,30 ailleurs).
- **ΔQ** : qualité de jeu. On prend, pour chaque équipe, la moyenne sur ses 10 derniers matchs de (xG pour − xG contre), puis on fait la différence entre domicile et extérieur.
- **Ouverture** Otot = somme des (xG pour + xG contre) des deux équipes, centrée sur 5,5.
- **Effet ligue** : indicatrices pour SP1, I1, D1 et F1 (la Premier League est la référence).
- **Niveau de buts de la ligue** : moyenne des buts à domicile et à l'extérieur sur les 380 derniers matchs de la ligue, centrée. Utilisé seulement dans le modèle de buts.

Toutes les moyennes glissantes sont décalées d'un match. `tests/test_fuite.py` falsifie un résultat et vérifie que les variables de ce match et des matchs antérieurs ne changent pas. Ce test a d'ailleurs détecté une petite fuite dans une version précédente : c_L était calculé sur toutes les saisons. Elle a été corrigée ; son effet sur la log loss était inférieur à 10⁻⁴.

## 4. Modèles

### 4.1 Résultat 1X2 : régression logistique multinomiale

```
z1 = log[P(1)/P(X)] = β1 · x        z2 = log[P(2)/P(X)] = β2 · x
P(X) = 1 / (1 + e^z1 + e^z2),  P(1) = e^z1 P(X),  P(2) = e^z2 P(X)
```

Estimation par maximum de vraisemblance pondérée, avec un poids w = 0,5^((s_ref − saison)/4) : un match d'il y a 4 saisons compte 2 fois moins.

### 4.2 Buts : Poisson + Dixon-Coles

- log λ_dom = α·x et log λ_ext = α'·x : deux GLM de Poisson avec les mêmes poids.
- P(score i-j) = Pois(i; λ_dom) · Pois(j; λ_ext) · τ(i, j), où τ corrige les scores 0-0, 1-0, 0-1 et 1-1 (Dixon & Coles 1997).
- ρ ≈ −0,055, estimé par maximum de vraisemblance.
- La grille 11×11 donne tous les marchés : over/under, BTTS, cage inviolée, score exact. Une simulation Monte-Carlo de 100 000 tirages vérifie la cohérence.
- **But en 1re mi-temps** : λ_MT = k·(λ_dom + λ_ext), avec k ≈ 0,44 estimé par maximum de vraisemblance. P = 1 − e^(−λ_MT).

### 4.3 Sorties complémentaires

- **Cote juste** = 1/p.
- **Comparaison aux cotes** : les probabilités du marché sont débarrassées de la marge par la méthode de Shin (1993).
- **Indice de fiabilité** : taux de réussite observé de l'issue favorite selon la confiance du modèle, sur le test 2021-2026.

| Confiance du modèle (p max) | ≤ 42 % | 42-50 % | 50-61 % | > 61 % |
|---|---|---|---|---|
| Issue favorite réalisée | 39 % | 46 % | 54 % | 71 % |

### 4.4 Corners et cartons : modèles de comptage

Données complètes à partir de 2008/09. Pour chaque statistique, on estime une régression de Poisson pondérée dans le temps pour la moyenne μ, puis un paramètre de dispersion α (loi binomiale négative, variance μ + αμ²) par maximum de vraisemblance.

| Cible | Variables |
|---|---|
| Corners du match (et de chaque équipe) | niveau de la ligue (log, 380 derniers matchs) ; corners obtenus et concédés par chaque équipe (10 derniers matchs) ; tirs pour et contre ; ΔElo, \|ΔElo\| ; ratings GAS |
| Cartons jaunes (match et équipes) | niveau de la ligue ; jaunes reçus et provoqués par chaque équipe ; fautes commises et subies ; ΔElo, \|ΔElo\| (les matchs serrés sont plus tendus) |
| Cartons rouges (match) | niveau de la ligue ; rouges et jaunes récents des deux équipes ; \|ΔElo\| |

- Les corners des deux équipes sont **négativement corrélés** (−0,24) : l'équipe qui domine obtient les corners. On modélise donc directement le **total**, puis on le répartit entre les équipes selon les modèles par équipe.
- α vaut environ 0,016 pour les corners et environ 0 pour les jaunes (quasi-Poisson), contre 0,38 pour les rouges, très surdispersés.

### 4.5 Aide à la décision : classement par niveau de risque

Pour chaque match, 30 marchés sont calculés à partir des modèles :
- 1X2 et double chance ;
- plus/moins de 1,5, 2,5 et 3,5 buts ; les deux équipes marquent ; chaque équipe marque ;
- corners : plus/moins de 8,5, 9,5 et 10,5 ; chaque équipe plus de 4,5 ;
- cartons : jaunes plus/moins de 3,5 et 4,5 ; rouge oui/non.

Ces marchés sont classés du moins risqué au plus risqué (risque = 1 − probabilité), en cinq paliers :

| Palier | Probabilité de réussite |
|---|---|
| 1 · très faible | ≥ 80 % |
| 2 · faible | 65-80 % |
| 3 · modéré | 50-65 % |
| 4 · élevé | 35-50 % |
| 5 · très élevé | < 35 % |

Trois « décisions » sont proposées pour chaque match :
- **prudente** : l'issue la plus probable, hors issues quasi certaines (au-delà de 95 %) ;
- **équilibrée** : l'issue la plus proche de 60 % ;
- **audacieuse** : l'issue la plus proche de 40 %.

Si l'utilisateur saisit des cotes, on calcule pour chaque marché :
- la probabilité implicite 1/cote ;
- l'écart entre le modèle et le marché ;
- la valeur attendue p × cote − 1.

**Le classement mesure le risque, pas la rentabilité.** Une issue peu risquée a une cote faible, et la valeur attendue n'est fiable que si le modèle l'est (voir `resultats.md` §5 et §10).

## 5. Protocole d'évaluation

| Période | Usage |
|---|---|
| 2006-2015 | Réglage des paramètres des ratings (GAS) |
| 2017/18-2020/21 | Sélection entre modèles candidats |
| **2021/22-2025/26** | **Évaluation rétrospective** (walk-forward). Test intact pour v3/v4 ; pour v5, les variables d'enjeu ont été étudiées sur 2010-2025, ce qui recoupe cette période |
| **2026/27 →** | **Évaluation prospective** : journal des prédictions figées avant le coup d'envoi, jamais utilisé pour un choix |

- **Walk-forward** : pour prédire la saison s, on entraîne sur toutes les saisons strictement antérieures.
- **Métriques** :
  - log loss (règle de score propre, critère principal) ;
  - RPS (tient compte de l'ordre 1 < X < 2) ;
  - Brier ;
  - ECE (calibration par déciles) ;
  - taux de bons résultats (indicatif seulement).
- **Significativité** : bootstrap apparié sur les différences match par match (2 000 rééchantillonnages, IC à 95 %).
- **Références** : fréquences des issues, Elo seul, versions précédentes v3/v4, et cotes des bookmakers (référence externe, jamais utilisées comme variable).
- **Mêmes matchs pour tous les modèles** : la comparaison officielle (`scripts/comparaison_commune.py`) note chaque modèle sur le même ensemble de matchs, construit avec les mêmes variables d'entrée.

## 6. Ce qui a été testé puis rejeté

| Piste | Résultat | Décision |
|---|---|---|
| Elo-buts et pi « réglés » sur 2015-2020 | Gain en sélection, **non reproduit** en test | Rejeté : surapprentissage de la sélection |
| Forces Dixon-Coles dynamiques (penaltyblog) | Redondantes avec GAS, 100 fois plus lentes | Rejeté |
| Ratings GAP (Wheatcroft) | Pas de gain | Rejeté |
| LightGBM, XGBoost, ensembles | Moins bons que le logit (0,984-0,986) | Rejeté |
| 38 à 112 variables (forme, tirs, corners, repos, confrontations directes) | Plateau, puis dégradation (surapprentissage) | Rejeté |
| Ré-entraînement hebdomadaire | +0,4 ×10⁻³ (non significatif) | Inutile : les ratings se mettent déjà à jour |
| Méthodes des guides de paris | Voir `docs/resultats.md` §7 | Deux idées retenues : niveau de buts de la ligue, marchés dérivés |
