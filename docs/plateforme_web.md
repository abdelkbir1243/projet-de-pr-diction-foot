# Plateforme web Goalgebra : architecture, mise à jour et déploiement

## 1. Architecture

```
             ┌──────────────────────────────── GitHub Actions (toutes les 2 h) ────────────────────────────────┐
historique ──┤  python -m footpred.web                                                                          │
(xgabora)    │    1. résultats récents ◄── football-data.co.uk (tirs, corners, cartons, cotes) · football-data.org │
             │    2. ratings (Elo, pi, GAS) ─► modèle v5 ─► analyses (contexte, stats attendues, comparables, cotes) │
             │    3. calendrier ◄── football-data.org (si clé) sinon football-data.co.uk (fixtures + cotes)          │
             │    4. web/data/*.json (+ journal.json : prédictions figées) ──commit──► Vercel redéploie              │
             └──────────────────────────────────────────────────────────────────────────────────────────────────┘
navigateur ──► Next.js (pages statiques) ──► /api/live (30-60 s, si clé football-data.org) : scores en direct
                                         └─► /api/assistant : assistant statistique (moteur local, Claude si clé)
```

- **Aucune donnée n'est simulée.** Si une source ne répond pas, le pipeline passe à la suivante (`footpred/sources.py`) ; si aucune ne répond, le site affiche les derniers résultats réels connus.
- **Le site** est statique : chaque page est pré-générée, donc rapide et bien indexée.
- **La couche de données** (`web/lib/data.ts`) est l'unique point d'accès aux JSON ; les types sont dans `web/lib/types.ts`.

### Modes de données (bandeau en haut du site)

| Mode | Quand | Ce qui s'affiche |
|---|---|---|
| `live` | clé football-data.org disponible | calendrier, reports, scores et minutes en direct (`/api/live`) |
| `fixtures` | sans clé, football-data.co.uk joignable | calendrier des prochains jours avec cotes, résultats publiés toutes les 2 h |
| `offline` | aucune source de calendrier joignable | derniers résultats réels, avec leurs prédictions hors échantillon |
| `replay` | `python -m footpred.web --rejeu AAAA-MM-JJ` | une journée passée rejouée : le modèle ne voit que les données antérieures, l'horloge du site est figée à cette date |

Le dépôt est livré avec des données réelles calculées le 12 octobre 2026 (mode `fixtures`). Le workflow GitHub Actions et l'application Streamlit les remplacent ensuite automatiquement par les données du jour.

### Sources (interchangeables)

| Source | Clé | Utilisation |
|---|---|---|
| football-data.co.uk | aucune | résultats de la saison en cours avec statistiques et cotes ; `fixtures.csv` : matchs des prochains jours et cotes d'avant-match |
| football-data.org | gratuite | calendrier, statuts, scores en direct ; résultats récents |
| dataset xgabora (GitHub) | aucune | historique 2000 → aujourd'hui, Elo ClubElo |
| openfootball/football.json (GitHub) | aucune | secours : calendrier complet de la saison des 5 championnats et scores (quelques jours de retard) |
| openfootball/champions-league (GitHub) | aucune | Ligue des champions (2011 →), Ligue Europa (2020 →), Conference League (2021 →) : résultats et calendrier publié |

L'ordre des sources de calendrier se règle avec la variable `GOALGEBRA_SOURCES` (par défaut `footballdata_org,football_data_co_uk,openfootball` ; openfootball reste toujours en dernier recours). Pour les matchs récents absents du dataset, l'Elo est prolongé avec la formule Elo classique à partir du dernier Elo ClubElo connu.

### Honnêteté des prédictions

- Chaque prédiction d'un match à venir est **figée dans `web/data/journal.json` avant le coup d'envoi** (modes `live` et `fixtures`).
- Après le match, la page affiche la prédiction figée (badge « Figée avant le match »).
- Un match terminé sans prédiction figée reçoit une prédiction **hors échantillon** : modèle entraîné uniquement sur les saisons précédentes, variables d'avant-match (badge « Hors échantillon »).
- La page **Performance IA** affiche le test historique et le bilan du suivi en conditions réelles.

### Coupes d'Europe

Ligue des champions, Ligue Europa et Conference League ont leur propre modèle (`footpred/coupes.py`) : écart d'Elo → logit 1X2
et Poisson–Dixon-Coles pour les buts, évalué saison par saison (`docs/resultats.md` §15). Les clubs hors des championnats suivis
ont un Elo estimé sur leurs matchs européens. Pas de corners, cartons ni cotes pour ces matchs. Le classement de la phase de ligue
(format 2024+) est calculé à partir des résultats. Le calendrier vient d'openfootball et, pour la Ligue des champions, de
football-data.org quand une clé est configurée (la Ligue Europa et la Conference League ne sont pas dans l'offre gratuite).

### Analyse d'un match

| Onglet | Contenu |
|---|---|
| Aperçu | probabilités, contexte (classement de la veille, repos, promu, champion en titre, enjeu de fin de saison), statistiques attendues avec intervalles à 80 %, distribution du nombre de buts, forme |
| Analyse IA | probabilités, notes, radar, facteurs clés, **matchs comparables** (ce qui s'est passé dans 400 matchs semblables) |
| Cotes | modèle vs marché : probabilités implicites des cotes (marge retirée, méthode de Shin), écarts, cote juste |
| Stats · H2H · Classement | comparaison des équipes, confrontations directes, classement |

La page **Cotes & risque** (`/markets`) classe toutes les issues des prochains matchs du moins au plus risqué, avec la fiabilité observée de chaque palier. Elle rappelle qu'aucun palier n'a été rentable aux cotes réelles sur 2021-2026.

### Assistant statistique

- Bouton « Assistant » dans l'en-tête, panneau sur toutes les pages, page `/assistant`.
- **Sans clé** : moteur local gratuit (`web/lib/assistant.ts`). Il reconnaît les équipes, les compétitions et les questions courantes (analyse d'un match, forme, classement, risque, fiabilité, glossaire) et répond uniquement avec les données publiées.
- **Avec `ANTHROPIC_API_KEY`** (variable Vercel, côté serveur) : Claude reformule et approfondit la réponse à partir des mêmes données, avec interdiction d'inventer des chiffres ou de conseiller un pari. Modèle réglable avec `ANTHROPIC_MODEL`. Limite de 20 questions par visiteur toutes les 10 minutes pour protéger la clé.

## 2. Mise en service (environ 20 minutes)

### a. GitHub

1. Envoyer le projet sur GitHub, avec le dossier `.github/` (caché). La méthode la plus sûre est GitHub Desktop.
2. Facultatif : clé gratuite football-data.org (https://www.football-data.org/client/register), à ajouter dans **Settings › Secrets and variables › Actions** sous le nom `FOOTBALL_DATA_API_KEY`. Sans elle, le calendrier et les cotes viennent de football-data.co.uk, sans score minute par minute.
3. Dans **Actions**, choisir **Publier les données** puis **Run workflow** pour un premier lancement. Ensuite, il s'exécute toutes les 2 heures.

### b. Vercel (hébergement gratuit du site)

1. Sur https://vercel.com, se connecter avec GitHub, cliquer sur **Add New…**, puis **Project**, et importer le dépôt.
2. **Root Directory** : `web`. Le framework Next.js est détecté automatiquement.
3. **Environment Variables** (toutes facultatives) :
   - `NEXT_PUBLIC_SITE_URL` = l'URL finale, par exemple `https://goalgebra.vercel.app` ;
   - `FOOTBALL_DATA_API_KEY` = la clé football-data.org (scores en direct) ;
   - `ANTHROPIC_API_KEY` = une clé de l'API Claude (assistant plus naturel ; payant à l'usage) ;
   - `ANTHROPIC_MODEL` = identifiant du modèle Claude si vous voulez changer celui par défaut.
4. Cliquer sur **Deploy**. Chaque commit du workflow redéploie ensuite le site automatiquement.

## 3. Développement local

```bash
python -m footpred.web --sortie web/data                     # données du jour (sources réelles)
python -m footpred.web --sortie web/data --rejeu 2025-11-05  # ou : rejouer une journée passée
cd web && npm install && npm run dev                          # http://localhost:3000
```

## 4. Structure du frontend

```
web/
├── app/                         pages (App Router), métadonnées SEO, sitemap, robots, image Open Graph
│   ├── page.tsx                 Match Center (accueil) — /matches identique
│   ├── match/[slug]/            dashboard d'un match (URL lisible : /match/manchester-city-vs-arsenal) : Aperçu · Analyse IA · Stats · H2H · Compos · Classement
│   ├── predictions/             prédictions à venir + historique ; /predictions/[slug] → onglet Prédiction du match
│   ├── competitions/, competition/[slug]/   cartes des compétitions ; Aperçu · Matchs · Classement · Statistiques · Équipes · Joueurs
│   ├── team/[slug]/, teams/     page club (/team/manchester-city) : Aperçu · Matchs · Effectif · Statistiques · Prédictions
│   ├── standings/, statistics/  classements (zones européennes, relégation, forme) ; comparaisons et palmarès statistiques
│   ├── ai-performance/          transparence : accuracy, Brier, log loss, calibration, évolution, historique réussi/manqué
│   ├── markets/                 Cotes & risque : issues classées par risque, désaccords modèle / marché
│   ├── assistant/, api/assistant/  assistant statistique (page + route serveur)
│   ├── profile/                 favoris et préférences
│   └── api/live/route.ts        scores en direct (proxy serveur, la clé ne quitte jamais le serveur)
├── components/
│   ├── chrome.tsx               Logo, Navbar sticky, SearchBar (⌘K), notifications, ProfileMenu, Sidebar repliable, BottomNavigation, Footer
│   ├── match-center.tsx         DateSelector, filtres, LeagueHeader, LeagueSection, MatchCard, MatchList, skeletons
│   ├── match-detail.tsx         orchestrateur de la page match (onglets)
│   ├── match/                   header, overview, ai-analysis, analysis-cards (contexte, attendus, comparables, cotes), team-comparison, h2h-card, timeline (stats réelles)
│   ├── assistant.tsx            panneau et page de l'assistant
│   ├── markets-view.tsx         page Cotes & risque
│   ├── football.tsx             TeamLogo, FormGuide, ProbabilityBar, MatchStatusBadge, AIBadge, FavoriteStar
│   ├── cards.tsx                PredictionCard, AIPerformanceMini, AIExplainer
│   ├── prediction-history.tsx   historique Match · Prédiction · Probabilité · Résultat réel · Correct/Incorrect (tableau / cartes mobile)
│   ├── charts.tsx               RadarChart, LineChart, Donut, CalibrationChart (Recharts)
│   ├── standings.tsx (StandingsTable), leaderboard.tsx, predictions-view.tsx, performance-view.tsx, profile-view.tsx
│   └── ui/                      primitives (Card, Badge, SkeletonCard, EmptyState, StatsCard, PageHeader…) et onglets synchronisés avec l'URL
├── lib/                         types, données, statut en direct, insights (ratings, facteurs clés), i18n FR/EN, favoris, utilitaires
└── data/                        JSON produits par le pipeline
```

**Identité visuelle.** Goalgebra est une identité originale :
- logo « trajectoire » ;
- couleur de marque indigo → violet (dégradé réservé aux éléments IA) ; vert et rouge uniquement pour les données positives / négatives ;
- thèmes clair et sombre (tokens CSS dans `app/globals.css`), mise en page utilisable dès 320 px ;
- couleurs dédiées aux probabilités : bleu pour le domicile, gris pour le nul, orange pour l'extérieur (palette vérifiée pour le daltonisme) ;
- écussons génériques à code de trois lettres, sans aucun logo officiel de club ni de compétition.

## 5. Limites actuelles et extensions prévues

- **Joueurs, compositions, effectifs, stades, entraîneurs** : non disponibles (l'onglet Compos a été retiré). Il faut une source de données joueurs, par exemple API-Football (payante au-delà de 100 requêtes/jour).
- **Heure des matchs issus de l'historique** : le dataset ne donne que la date ; l'heure s'affiche « --:-- » (rejeu, hors ligne).
- **Ligue des champions** : calendrier et scores affichés, mais pas de prédiction, car le modèle est entraîné sur les championnats nationaux.
- **Comptes et notifications** : retirés (ils n'étaient pas branchés). Les favoris sont stockés dans le navigateur.
- **Langue** : interface en français uniquement, comme les analyses générées.
