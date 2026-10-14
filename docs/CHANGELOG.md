# Journal des versions

## 5.4.0 — plateforme de prédiction scientifique, Sélection du jour

- Validité temporelle : états `scheduled / prematch_open / live / awaiting_result / finished / postponed / cancelled`, type et
  traçabilité de chaque prédiction, horaire fiable obligatoire pour figer, filtres Next.js corrigés.
- Banc d'essai (`footpred/banc.py`, `scripts/banc_generer.py`, `scripts/banc_evaluer.py`) : prédictions hors échantillon
  chronologiques, matrice E0-E8, calibration (température, multinomiale, isotonique), ablations, bootstrap, test final réservé 2025/26.
  Résultats honnêtes : ni CatBoost, ni l'ensemble, ni la combinaison avec le marché n'améliorent la validation.
- Moteur de sélection (`footpred/selection.py`, `selection_prod.py`) : distribution conjointe cohérente, 17 marchés, méta-modèle,
  borne basse, désaccord, entropie, qualité des données, seuils appris sur la validation, abstention.
- Page **Sélection du jour** (page d'accueil), route API `/v1/daily-selections`, sélection figée au journal avant le coup d'envoi,
  suivi sur la page Performance.
- xG : `xgProxy*` / `xgSource` (statistique approchée) distincts de `goalsLambda` (buts attendus du modèle).
- Versions unifiées (`footpred/version.py`), interface du futur modèle live (`footpred/live_interface.py`), fiches modèle et données.

## 5.3.0 — mode plateforme (serveur)

- `plateforme/` : base de données (SQLAlchemy ; PostgreSQL en production, SQLite en local), comptes (bcrypt, anti force brute,
  sessions révocables par cookie), équipes suivies, clés d'API (empreinte SHA-256, quotas), worker de calcul supervisé avec
  alertes, import du journal en base, API publique FastAPI (`/docs`).
- Application : pages « Mon compte » et « Administration », bouton « Suivre » et filtre « Mes équipes », Laboratoire réservé aux
  administrateurs, mode privé facultatif, connexion Google facultative (`st.login`).
- Déploiement : `Dockerfile`, `deploy/docker-compose.yml` (Caddy HTTPS, app, api, worker, PostgreSQL, sauvegardes),
  `deploy/installer_serveur.sh` (pare-feu, fail2ban, SSH par clé, Docker), guide `docs/deploiement_serveur.md`.
- Tests : `tests/test_plateforme.py` (comptes, sessions, quotas, API, journal) ; CI : construction de l'image Docker.

## 5.2.0 — corrections issues de la revue

- **Journal honnête** : une prédiction n'est enregistrée qu'avant le coup d'envoi (`figeable`), les entrées invalides des
  versions précédentes sont retirées (`nettoyer_journal` ; 46 entrées supprimées), et un test vérifie `madeAt < kickoff`
  sur le journal publié (`tests/test_journal.py`).
- **Matchs commencés** : plus de nouvelle prédiction après le coup d'envoi ; état `started` / `awaitingResult` (« en attente du
  résultat ») ; exclus des prédictions à venir et de `markets.json`.
- **Protocole** : 2021-2026 est présenté comme **évaluation rétrospective** (les variables de v5 ont été étudiées sur 2010-2025) ;
  l'évaluation **prospective** est le journal 2026/27.
- **Comparaison sur les mêmes matchs** : `scripts/comparaison_commune.py` note Elo, v3, v4, v5 et les cotes sur les mêmes 8 896 matchs.
- **Fraîcheur** : `meta.freshness` (dernier résultat, matchs joués sans score, retard) et bandeau « données en retard »
  (Streamlit et site web) ; saison des coupes marquée « dernière saison disponible » quand la source n'a pas publié la saison en cours.
- **Pipeline** : GitHub Actions est le pipeline principal ; l'application ne recalcule qu'en secours (données > 6 h) en conservant le
  journal ; pas de commit quand seule l'horodatation change (sauf toutes les 5 h). Mémoire documentée : ~1,1 Go pendant un calcul.
- **Dépendances** : `pandas>=2.2` ; `requirements-research.txt` (xgboost) pour les scripts d'étude.
- **Étude StatsBomb** : grille xT sans fuite en B et C (estimée sur les seuls matchs antérieurs) ; conclusions inchangées.

## 5.1.0

Application Streamlit au style Goalgebra (pages Matchs, Fiche match avec onglet xG & forme, Équipes, Assistant, Méthode),
mise à jour automatique, source de secours openfootball, tests des pages.
