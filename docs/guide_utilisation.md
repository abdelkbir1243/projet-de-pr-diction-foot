# Guide d'utilisation

## A. Première mise en route (une fois)

1. **Publier le dépôt sur GitHub** : créer un dépôt vide `football-prediction-stat` sur ton compte, puis :
   ```bash
   cd football-prediction-stat
   git init && git add . && git commit -m "Modèle statistique v4 — structure du projet"
   git branch -M main
   git remote add origin https://github.com/abdelkbir1243/football-prediction-stat.git
   git push -u origin main
   ```
   Si tu choisis un autre nom de dépôt, change la variable `DEPOT` dans la 1re cellule de chaque notebook.
2. **Vérifier que tout fonctionne** : `python -m pytest tests`. Les 9 tests doivent passer.
3. **Reproduire les résultats du rapport** : `python scripts/reproduire.py`, en 2 à 3 minutes. Les tables et figures sont écrites dans `results/`.

## B. Routine hebdomadaire (suivi en direct)

| Quand | Action | Outil |
|---|---|---|
| Lundi à jeudi, **avant** la journée | Relancer le modèle (données fraîches), saisir les affiches et enregistrer les prédictions | notebook 04, section 1, ou `python -m footpred journee "Dom vs Ext@AAAA-MM-JJ" …` |
| 3 à 5 jours **après** la journée | Évaluer les matchs joués | notebook 04, section 2, ou `python -m footpred evaluer` |
| Chaque mois | Copier `journal_evalue.csv` dans `results/` et commenter l'évolution dans le rapport | — |

Règles pour garder un suivi valable scientifiquement :
- **Ne jamais modifier** une ligne du journal après coup. L'horodatage prouve que la prédiction est antérieure au match.
- **Tout prédire**, pas seulement les matchs « sûrs ». Sinon, on crée un biais de sélection.
- **Attendre au moins 30 matchs**, et idéalement 200 ou plus, avant de conclure. Sur une semaine, le hasard domine (voir `docs/resultats.md` §4 : l'écart hebdomadaire avec les cotes varie de −0,02 à +0,04).
- **Vérifier la date `donnees_au`**. Si elle est vieille de plus de 7 jours, les derniers résultats ne sont pas encore intégrés.

## C. Noms des équipes

Utiliser les noms exacts du dataset, par exemple `Paris SG`, `Bayern Munich`, `Ath Madrid`, `Nott'm Forest`, `Inter`, `Milan`. En cas de faute, le programme propose les noms proches.
Pour lister les équipes d'une ligue :
```python
pred.d.X[pred.d.X.Division == "F1"].HomeTeam.unique()
```

## D. Tester une autre saison ou d'autres ligues

Dans le notebook 03, modifier `SAISON = 2023` ou `LIGUES = ["SP1", "F1"]`. En ligne de commande : `python -m footpred saison 2023`.

## E. Modifier le modèle proprement

1. Changer un paramètre dans `footpred/config.py`, ou ajouter une variable dans `features.py`.
2. Lancer `python -m pytest tests` pour vérifier l'absence de fuite.
3. Comparer à v4 avec `labo.validation(d)`. **Attention** : le test 2021-2026 a déjà servi. Pour un choix honnête, sélectionner sur 2017-2020 (`labo.validation(d, [2017, 2018, 2019, 2020])`), puis confirmer une seule fois sur 2021-2026 et sur le suivi en direct.
