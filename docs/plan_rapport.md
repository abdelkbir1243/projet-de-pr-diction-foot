# Plan du rapport et correspondance avec le dépôt

Chaque chapitre indique la source (notebook, table ou figure) qui fournit son contenu.

| # | Chapitre | Contenu | Sources dans le dépôt |
|---|---|---|---|
| 1 | **Introduction** | Problématique : estimer des probabilités de résultats, pas « deviner » un vainqueur. Objectifs, contraintes (aucun pari, reproductibilité) | README |
| 2 | **État de l'art** | Modèles de Poisson (Maher 1982, Dixon & Coles 1997) ; ratings (Elo, pi, GAS) ; apprentissage automatique (Hubáček 2019, Bunker 2024) ; données d'événements et xT (Hassard & Kerr 2024, Singh 2018) ; difficulté des matchs et Kelly Index (Ren & Susnjak 2022) ; protocole de référence face au marché (Sallis, Georgoulas & Tsoulos 2026) ; métriques (Constantinou & Fenton 2012, RPS) ; efficience du marché (Štrumbelj 2014, Kaunitz 2017) | `docs/references.md` |
| 3 | **Données et analyse exploratoire** | Source et couverture ; distribution des issues (≈ 44 % domicile, 25 % nuls, 31 % extérieur) ; buts ; avantage du terrain ; corrélations | `notebooks/01_exploration_donnees.ipynb` |
| 4 | **Méthodologie** | Ratings, variables sans fuite, logit multinomial, Poisson + Dixon-Coles, pondération temporelle, marchés dérivés | `docs/methodologie.md`, `notebooks/02` §1-2, `results/tables/formules_modele_final.csv` |
| 5 | **Protocole d'évaluation** | Découpage réglage / sélection / test ; walk-forward ; log loss, RPS, ECE ; bootstrap apparié ; test automatique d'absence de fuite | `docs/methodologie.md` §5, `tests/test_fuite.py` |
| 6 | **Résultats** | 6.1 Test 2021-2026 (tableau et figure) ; 6.2 marchés de buts ; 6.3 stabilité par ligue et par saison ; 6.4 calibration ; 6.5 saison 2025/26 figée et semaine par semaine | `docs/resultats.md` §1-4, `results/figures/*.png`, `notebooks/03` |
| 7 | **Expériences et discussion** | 7.1 Ce qui n'a pas marché (ML complexe, 112 variables : surapprentissage) ; 7.2 efficience du marché (stratégies simulées) ; 7.3 méthodes des guides de paris confrontées aux données ; 7.4 contexte des matchs (v5) et degré de confiance ; 7.5 données d'événements StatsBomb : reproduction de Hassard & Kerr (2024), 65 % avec les données du match contre 49 % avant le match ; 7.6 Kelly Index et méthodes de retrait de la marge (Ren & Susnjak 2022 ; Sallis et al. 2026) ; 7.7 coupes d'Europe (modèle Elo) et fatigue après un match européen | `docs/resultats.md` §5-7, §11-15, `notebooks/05`, `scripts/etude_statsbomb.py` |
| 8 | **Validation en conditions réelles** | Journal des prédictions horodatées, évaluation au fil des semaines | `notebooks/04`, `journal/journal_evalue.csv` |
| 9 | **Limites et perspectives** | Données manquantes (compositions, blessures, xG réels) ; coupes et matchs internationaux ; modèles bayésiens dynamiques ; données joueurs | README « Limites » |
| 10 | **Conclusion** | Modèle calibré et transparent, qui parcourt environ 90 % du chemin entre « aucune information » et le marché (log loss 1,074 → 0,982, contre 0,972 pour les cotes) | — |
| A | **Annexes** | Formules complètes, coefficients, guide d'utilisation, historique des versions v1 → v4 | `docs/guide_utilisation.md`, `docs/resultats.md` §8 |

## Figures prêtes à insérer

- `results/figures/validation_2021_2026.png` : log loss cumulée, calibration, comparaison par ligue.
- `results/figures/saison_2025.png` : même figure pour la saison 2025/26.
- `results/figures/hebdo_2025.png` : suivi semaine par semaine contre les cotes.
- Notebook 05 : rendement des stratégies simulées avec intervalles de confiance.

## Messages clés à défendre

1. La **log loss** est le bon critère : elle récompense des probabilités justes, pas des paris chanceux. Le taux de bons résultats seul est trompeur.
2. **La complexité ne paie pas** : un logit transparent avec de bons ratings bat LightGBM avec 112 variables.
3. **La rigueur du protocole** (walk-forward, test intouché, bootstrap, test de fuite) est la contribution méthodologique principale.
4. **Honnêteté des résultats** : le modèle ne bat pas le marché, et on explique pourquoi (information manquante).
5. **Expliquer n'est pas prédire** : avec les statistiques du match lui-même, on « prédit » 65 % des résultats (Hassard & Kerr 2024, reproduit) ; avec les seules informations disponibles avant le coup d'envoi, on tombe à 49-52 %. Beaucoup d'articles annonçant plus de 60 % mesurent en réalité la première chose.
6. **Nos conclusions sont confirmées à grande échelle** : Sallis et al. (2026), sur 225 474 matchs, trouvent eux aussi que l'algorithme compte peu et qu'aucun modèle ne fait mieux que les cotes sans marge.
