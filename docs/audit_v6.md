# Goalgebra 5.4 — audit, protocole scientifique et Sélection du jour

Ce document suit l'ordre des livrables demandés. Tous les chiffres viennent de `docs/resultats_v6.md`, généré par
`scripts/banc_generer.py` puis `scripts/banc_evaluer.py` (reproductibles, graine fixe pour CatBoost).

## 1. Audit synthétique de l'état de départ (5.3)

- **Modèle** : logit multinomial 1X2 (Elo, xG proxy, pi-ratings, ratings de buts GAS, effets ligue, enjeu de fin de saison) et
  Poisson + Dixon-Coles pour les buts. Bien calibré, bat Elo seul, reste moins bon que les cotes.
- **Validité temporelle** : journal déjà protégé (prédiction figée avant le coup d'envoi depuis 5.2), mais pas d'états de match
  explicites, pas de type de prédiction, horaire non fiable non exclu, et un filtre Next.js laissait des matchs commencés parmi
  les « prédictions à venir ».
- **Cohérence des marchés** : les probabilités 1X2 venaient du logit, les marchés de buts de la grille Dixon-Coles — deux modèles
  différents, donc des incohérences possibles (ex. double chance ≠ P(1)+P(N) de la grille).
- **Confiance** : niveaux A/B/C utiles mais construits à la main ; pas de borne basse, pas d'abstention formelle, pas de couverture.
- **Versions** : `pyproject` 5.3.0, `__version__` 4.0.0, métadonnées « v5.0 », méthodologie titrée « v4 ».
- **Source affichée en dur** dans le bandeau du site (« football-data.co.uk ») même quand la source réelle était openfootball.

## 2. Défauts critiques corrigés

| Fichier | Problème | Solution | Risque | Test | Résultat |
|---|---|---|---|---|---|
| `footpred/web.py` | pas d'états ni de traçabilité des prédictions | `etat()` : scheduled, prematch_open, live, awaiting_result, finished, postponed, cancelled ; chaque prédiction porte `predictionType`, `createdAt`, `modelVersion`, `dataVersion`, `predictionId` | faible (champs ajoutés) | `test_etats_des_matchs` | états publiés dans `matches.json` |
| `footpred/web.py` | un match à horaire inconnu pouvait être figé | `figeable` exige `timeKnown` | faible | `test_horaire_non_fiable_jamais_fige` | ✔ |
| `web/components/predictions-view.tsx`, `web/lib/status.ts` | un match commencé restait dans « à venir » (côté client) | `isPrematchOpen` (coup d'envoi futur, horaire fiable, ni commencé ni en attente) | faible | `tsc` + build | ✔ |
| `web/components/chrome.tsx` | source affichée en dur | bandeau construit depuis `meta.sources` | nul | build | ✔ |
| `footpred/version.py`, `pyproject.toml`, API | versions incohérentes | version unique 5.4.0 / modèle v5.4, reprise partout | nul | `test_versions_coherentes` | ✔ |
| `footpred/selection.py` | marchés incohérents entre eux | matrice des scores repondérée sur les probabilités 1X2 retenues ; 17 marchés dérivés de la même matrice | moyen (changement de méthode) | `test_distribution_conjointe_coherente` | identités exactes (1X = 1+N, over+under = 1, BTTS ≤ min) |
| `scripts/etude_statsbomb.py` | grille xT estimée sur toute la saison | grilles estimées sur les seuls matchs antérieurs (5.2) | — | relance de l'étude | conclusion inchangée |
| xG | confusion possible xG / buts attendus du modèle | champs `xgProxyFor/Against` + `xgSource` (statistique observée approchée) et `goalsLambda` (λ du modèle) ; libellés « buts attendus (λ) » | nul | — | ✔ |

## 3. Architecture cible (progressive, sans réécriture)

```
Collecteurs (football-data.org · football-data.co.uk · openfootball · dataset historique)
      ↓  worker (plateforme/worker.py, toutes les 2 h)
Pipeline footpred (variables point-in-time : shift(1), saisons antérieures uniquement)
      ↓
Modèles : E0 logit v5 (production) · E2 Dixon-Coles (distribution des scores) · E1 et E3 (désaccord) · marché (référence)
      ↓
Moteur de sélection (footpred/selection*.py, artefact appris sur la validation)
      ↓
JSON publiés + PostgreSQL (journal immuable, comptes, clés) → API FastAPI (/v1/…, /v1/daily-selections) → Streamlit / Next.js
```

Redis n'est pas ajouté : aucun besoin mesuré (le cache par fichier et les quotas en base suffisent au trafic actuel).
Le modèle live (Phase 6) a son interface prête (`footpred/live_interface.py`) mais n'est pas activé, faute de flux d'événements.

## 4. Schéma des données ajoutées

- `matches.json` → par match : `state`, `started`, `awaitingResult` ; `prediction.{predictionType, createdAt, modelVersion,
  dataVersion, predictionId, goalsLambda}` ; `selection` (détail complet : candidats, modèles, désaccord, entropie, contrôles de
  qualité, explication, scores) pour les matchs `prematch_open`, ou la sélection figée (`fige: true`, `resultat`) ensuite.
- `selections.json` → par date (Europe/Paris) : `matches`, `retained`, `prudent`, `abstentions`, `coverage`,
  `meanConfidenceRetained`, `mostPredictable`, `reasons`, `freshness`, `items[]` (version compacte).
- `journal.json` → `selection` immuable : `decision`, `choix{cle, marche, famille, p, p_bas, ref, ref_source, ecart, info, cote, ev,
  ev_prudente}`, `plusProbable`, `confiance`, `qualite`, `desaccord`, `entropie`, `raisons`, `createdAt`, `modelVersion`,
  `dataVersion`, `selectionId`, puis `resultat` (1/0) une fois le match terminé.
- `footpred/artefacts/selection.json` → ensemble (empilement), méta-modèle (coefficients et covariance), seuils, fréquences des
  marchés (fenêtre A), fiabilité par famille (validation), résumé du test final.

## 5. Plan scientifique et résultats (Phase 2-3)

Découpage strictement chronologique : **A** 2016-2020 (premières années d'empilement), **B** 2021-2024 (validation),
**T** 2025/26 (test final réservé, aucune décision n'y est prise), puis **prospectif** 2026/27 (journal). Pour chaque saison,
chaque modèle est entraîné sur les saisons antérieures uniquement ; l'empilement d'une saison t est appris sur les prédictions
hors échantillon des saisons < t. Mêmes matchs pour tous (cotes disponibles), IC 95 % par bootstrap apparié.

**Test final T 2025/26 (1 752 matchs)** — log loss : marché 0,9784 · E6 sport+marché 0,9780 · **E0 0,9884** · E3 CatBoost 0,9897 ·
E7 ensemble 0,9896 · E2 Dixon-Coles 0,9897 · E1 0,9909 · Elo 0,9961 · fréquences 1,0718.

| Expérience | Verdict (validation B, confirmé ou non sur T) |
|---|---|
| E0 actuel vs Elo | E0 meilleur : −3,35 ×10⁻³ [−6,16 ; −0,53] sur B, −7,67 [−13,37 ; −1,96] sur T |
| E1 logistique Elo + forme | moins bon que E0 |
| E2 Dixon-Coles (1X2 dérivé) | proche de E0, non significatif ; conservé pour la distribution des scores |
| E3 CatBoost | **moins bon** que E0 sur B (+2,69 [+0,70 ; +4,66]) ; non retenu |
| E4 vrai xG | **non réalisé** : aucune source gratuite et fiable joignable ; interface `xgProxy*` / `xgSource` prête |
| E5 marché seul | meilleure référence (≈ −10 ×10⁻³ par rapport à E0) |
| E6 sport + marché | **n'améliore pas** le marché (+0,18 [−0,58 ; +0,91] sur B) : Goalgebra n'apporte pas d'information au-delà des cotes |
| E7 ensemble calibré | **moins bon** que E0 sur B (+1,21 [+0,12 ; +2,33]) ; règle « ne combiner que ce qui améliore la validation » → non utilisé |
| E8 ensemble + abstention | voir §6 |

Calibration de E0 (B + T, 8 897 matchs) : brut ECE 0,0113, température 0,0109, multinomiale 0,0146, isotonique 0,0144 ; pentes
0,95-1,00 : E0 est déjà bien calibré, aucune recalibration n'améliore la log loss. Ablations (B) : retirer Elo (+1,29) ou la forme/xG
proxy (+2,15, et +4,29 sur T) dégrade significativement ; pi-ratings, GAS, enjeu, effets ligue : non significatifs.

## 6. Moteur de confiance et Sélection du jour (Phase 4-5)

1. **Probabilités 1X2** : E0 (l'ensemble ne bat pas E0 en validation).
2. **Distribution conjointe** : matrice Dixon-Coles repondérée pour que P(1), P(N), P(2) égalent E0 ; 17 marchés en découlent.
3. **Méta-modèle** (appris sur B) : P(sélection correcte | logit p, famille, désaccord, entropie, saison installée). Résultat :
   coefficient de logit(p) = 1,016 (0,009), les autres non significatifs → les probabilités sont déjà fiables ; la **borne basse**
   (95 % unilatérale) combine l'incertitude du méta-modèle et la **dispersion des modèles de base** pour le marché considéré.
4. **Référence** : probabilité du marché sans marge (Shin) si le marché est coté (1X2 et dérivés, plus/moins 2,5), sinon fréquence
   historique du marché (fenêtre A). **Information** = divergence de Kullback-Leibler en bits.
5. **Décision** : *retenue* si informative (≥ κ bits), borne basse ≥ τ **et** supérieure à la référence, désaccord ≤ δ, qualité
   suffisante ; *prudente* si p ≥ τ_p et p > référence ; sinon *abstention*. Contrôles bloquants : horaire fiable, données à
   jour, variables complètes.
6. **Seuils appris sur B** (cibles produit documentées : retenues ≥ 85 % de réussite dans *chaque* saison, prudentes ≥ 75 %,
   écart de calibration ≥ −2 points ; objectif : couverture maximale) : τ = 0,79, κ = 0,02 bit, δ = 1,0 (le désaccord n'a pas
   d'effet mesurable une fois p connu ; il agit via la borne basse), τ_p = 0,69.

**Test final réservé T 2025/26 (1 752 matchs, mode « meilleur compromis »)**

| Décision | Part des matchs | Réussite observée | Probabilité annoncée | Référence | Succès en plus de la référence |
|---|---|---|---|---|---|
| Retenue | 58,6 % | **88,1 %** | 86,7 % | 73,1 % | +15,0 points |
| Prudente | 17,3 % | 75,5 % | 77,8 % | 68,5 % | +7,0 points |
| Abstention | 24,1 % | (91,5 %)* | 92,1 % | 93,2 % | −1,7 point |
| Tous les matchs, 1X2 le plus probable | 100 % | 51,8 % | 52,5 % | 51,8 % | 0 |

\* réussite de la sélection *la plus probable* (souvent « plus de 0,5 but »), qui n'apporte aucune information : c'est pour cela
qu'elle est écartée. Les sélections retenues sont surtout « une équipe marque au moins un but » (83 %) et des marchés de buts :
c'est là que le modèle sait le plus de choses par rapport à la référence ; aucune n'a de cote observée, donc **aucune valeur
statistique face au marché ne peut être affirmée**. Sur les marchés cotés, le modèle n'apporte pas d'information au-delà des cotes
(E6).

## 7. Tests ajoutés (65 au total)

`tests/test_journal.py` (états, horaire, figement), `tests/test_selection.py` (cohérence des marchés, décisions, abstention,
borne basse, déterminisme, référence sans cote, sélection figée avant le coup d'envoi et jamais remplacée par le live, fenêtres
disjointes, cohérence des fichiers publiés), `tests/test_versions.py`, API `/v1/daily-selections` (`tests/test_plateforme.py`),
page Streamlit (`tests/test_app_streamlit.py`). Anti-fuite du banc : assertion `max(date entraînement) < min(date test)` à chaque
saison (`footpred/banc.py`), plus `tests/test_fuite.py` existant.

## 8. Limites restantes

- Pas de vrai xG ni de compositions, blessures, suspensions horodatées : le modèle reste moins précis que le marché.
- T n'est pas parfaitement vierge pour E0 (variables d'enjeu étudiées jusqu'en 2025) ; la seule évaluation totalement
  prospective est le journal 2026/27.
- Les sélections retenues portent rarement sur des marchés cotés : leur « valeur » face aux bookmakers n'est pas mesurable avec
  des données gratuites (pas de cotes « équipe marque », pas de cotes de clôture).
- Seuils cibles (85 % / 75 %) = choix produit ; d'autres cibles donnent d'autres couvertures (`results/tables/v6_grille_seuils.csv`).
- Pas de modèle live (Phase 6) ; pas de SHAP non linéaire (le modèle en production est linéaire : contributions exactes affichées).
- Le pipeline entraîne deux modèles de plus (E1, CatBoost) pour mesurer le désaccord : quelques secondes et ~100 Mo en plus.

## 9. Recommandations pour la version suivante

1. Brancher un fournisseur de xG et de compositions horodatées, puis rejouer E4 sur le même protocole.
2. Collecter les cotes de clôture (CLV) et des marchés « équipe marque / BTTS » pour mesurer la valeur des sélections.
3. Suivre le journal 2026/27 : réussite par décision et par famille, recalibrer le méta-modèle chaque été sur la saison écoulée.
4. Phase 6 : dataset d'instantanés (15/30/45/60/75), modèle de buts restants, évaluation par minute.
