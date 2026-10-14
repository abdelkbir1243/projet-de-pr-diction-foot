# Fiche données — Goalgebra v5.4

| Source | Licence / accès | Contenu | Fraîcheur | Utilisation |
|---|---|---|---|---|
| xgabora/Club-Football-Match-Data (GitHub) | public | matchs 2000 → aujourd'hui : scores, tirs, corners, cartons, cotes moyennes, Elo ClubElo | quelques semaines de retard | historique d'entraînement |
| football-data.co.uk | gratuit | résultats de la saison avec statistiques et cotes ; calendrier des prochains jours | quotidienne | résultats récents, cotes |
| football-data.org | clé gratuite | calendrier, statuts, scores en direct | minutes | calendrier et scores (si clé) |
| openfootball/football.json, champions-league | domaine public | calendrier complet, scores (retard de quelques jours), coupes d'Europe | variable | secours sans clé, coupes |
| StatsBomb Open Data | licence non commerciale | événements 2015/16 | figée | étude uniquement (pas en production) |

- **Contrôles** : `meta.freshness` (dernier résultat, matchs joués sans score, retard en jours) ; au-delà, bandeau « données en
  retard » et suspension des sélections (contrôle bloquant « données à jour »).
- **Horodatage** : chaque prédiction et chaque sélection portent `createdAt` et `dataVersion` (date des dernières données + nombre
  de résultats ajoutés). Le journal refuse toute entrée postérieure au coup d'envoi.
- **Biais connus** : cotes moyennes (pas de cotes de clôture) ; promus moins bien estimés en début de saison ; horaires inconnus
  pour les matchs historiques (exclus des prédictions d'avant-match publiées).
- **Données personnelles** : aucune dans les données sportives ; comptes de la plateforme : e-mail, nom facultatif, équipes suivies.
