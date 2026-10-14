# Fiche modèle — Goalgebra v5.4

| Élément | Valeur |
|---|---|
| Tâche | probabilités d'avant-match P(1), P(N), P(2) et distribution des scores ; sélection statistique avec abstention |
| Modèle en production | E0 : régression logistique multinomiale pondérée dans le temps (demi-vie 4 saisons) ; buts : deux Poisson + ρ de Dixon-Coles |
| Modèles auxiliaires | E1 (logit Elo + forme), E3 (CatBoost, graine 0) : uniquement pour mesurer le désaccord entre modèles |
| Variables | Elo, xG proxy (tirs cadrés × conversion de la ligue), pi-ratings, ratings de buts GAS, effets ligue, enjeu de fin de saison — toutes calculées avec l'information strictement antérieure au match |
| Couverture | Premier League, LaLiga, Serie A, Bundesliga, Ligue 1 (coupes d'Europe : modèle Elo séparé, hors Sélection du jour) |
| Entraînement | toutes les saisons jouées depuis 2005/06 ; artefact de sélection appris sur 2016-2024 (`footpred/artefacts/selection.json`) |
| Évaluation | rétrospective walk-forward 2021-2025, test final réservé 2025/26, prospective 2026/27 (journal) — `docs/resultats_v6.md` |
| Performance (T 2025/26) | log loss 0,988 (marché 0,978, fréquences 1,072) ; bonne issue 51,8 % ; ECE 0,031 |
| Sélection (T 2025/26) | 58,6 % de matchs retenus, 88,1 % réussies pour 86,7 % annoncées ; 24 % d'abstentions |
| Limites | pas de compositions, blessures, vrai xG ; moins précis que les cotes ; pas de modèle live |
| Usage prévu | information probabiliste et pédagogique ; **aucun conseil de pari, aucune garantie** |
| Usage déconseillé | paris, combinaisons de sélections (dépendances non modélisées), décisions financières |
