# Déployer l'application sur Streamlit Community Cloud (gratuit)

L'application `app.py` reprend l'interface du site Goalgebra (mêmes cartes, couleurs et niveaux de confiance) et lit les fichiers publiés dans `web/data/*.json` : elle démarre en quelques secondes, sans entraîner de modèle.

Menu **Goalgebra** :
- **Matchs** (accueil) : choix du jour (◀ ▶), filtres, analyse de la journée avec intervalles à 80 %, matchs par compétition, prédictions à la une ;
- **Fiche match** (clic sur un match) : onglets Aperçu, Analyse IA, xG & forme, Cotes, H2H, Classement ;
- **Prédictions IA**, **Équipes** (profil, xG, Elo, derniers et prochains matchs), **Compétitions**, **Cotes & risque**,
  **Assistant** (questions en français), **Performance de l'IA**.

Menu **Étude** : **Méthode et limites**, et **Laboratoire du modèle** (l'ancienne application : prédire un match ou une journée
en recalculant le modèle, 1 à 2 minutes au premier accès).

## Secrets (tous facultatifs)

Streamlit Cloud → ton application → ⋮ → *Settings* → *Secrets* (modèle : `.streamlit/secrets.toml.example`) :

| Secret | Effet |
|---|---|
| `FOOTBALL_DATA_API_KEY` | calendrier officiel et **scores en direct** (football-data.org, clé gratuite) |
| `ANTHROPIC_API_KEY` | l'assistant rédige ses réponses avec Claude (sinon : moteur local gratuit) |
| `GOALGEBRA_MAJ_AUTO = "0"` | désactive le calcul dans l'application (données de GitHub Actions uniquement) |

## Mise à jour des données

Le pipeline principal est le workflow GitHub Actions « Publier les données » (toutes les 2 heures). En **secours**, si les données
affichées ont plus de 6 heures (workflow en panne ou désactivé), l'application lance elle-même en arrière-plan la récupération des
matchs du jour puis le calcul du modèle v5 (3 à 8 minutes ; on continue de voir les données précédentes, puis la page se recharge).
Le bouton **🔄 Mettre à jour** relance ce calcul à la demande. Un bandeau **« données en retard »** apparaît quand une source
publie les résultats avec retard (matchs joués depuis plus de 36 h sans score, ou dernier résultat trop ancien).

**Honnêteté du journal** : une prédiction n'est enregistrée qu'avant le coup d'envoi. Après le coup d'envoi, un match sans score
passe « en attente du résultat » : il sort des prédictions à venir et de la page Cotes & risque, et seule sa prédiction figée
(s'il y en a une) reste affichée.

Sources, dans l'ordre (la suivante prend le relais si une source ne répond pas) :
1. **football-data.org** : calendrier et scores en direct. Clé gratuite (https://www.football-data.org/client/register),
   à coller dans Streamlit Cloud → *App settings → Secrets* :
   ```toml
   FOOTBALL_DATA_API_KEY = "ta_clé"
   ```
2. **football-data.co.uk** (sans clé) : résultats avec statistiques, calendrier des prochains jours et cotes ;
3. **openfootball** (sans clé, hébergé sur GitHub) : calendrier complet de la saison et scores (quelques jours de retard).

En complément, le workflow GitHub Actions « Publier les données » recalcule `web/data` toutes les 2 heures et le pousse sur
GitHub (onglet *Actions*, permissions *Read and write*) ; il ne crée pas de commit quand seule l'horodatation a changé (sauf toutes
les 5 h). Le calcul utilise **environ 1,1 Go** de mémoire : si l'application manque de mémoire sur Streamlit Cloud, ajoute le secret
`GOALGEBRA_MAJ_AUTO = "0"` (configuration recommandée quand GitHub Actions fonctionne) : elle se contentera des données publiées.


## 1. Tester en local
```bash
pip install -r requirements.txt
streamlit run app.py
```
L'application s'ouvre sur http://localhost:8501. Les pages Goalgebra s'affichent immédiatement ; seul le Laboratoire recalcule le modèle.

Version de Python conseillée sur Streamlit Cloud : **3.11 ou 3.12** (*Advanced settings* au moment du déploiement).

## 2. Mettre le projet sur GitHub
Le dépôt doit être **public** pour l'offre gratuite. Voir `docs/guide_utilisation.md` §A.

## 3. Déployer
1. Aller sur https://share.streamlit.io et se connecter avec son compte GitHub.
2. Cliquer sur **Create app**, puis **Deploy a public app from GitHub**.
3. Renseigner :
   - Repository : `abdelkbir1243/football-prediction-stat`
   - Branch : `main`
   - Main file path : `app.py`
   - App URL : au choix, par exemple `prediction-foot-v4`
4. Dans **Advanced settings**, choisir Python 3.11 ou 3.12.
5. Cliquer sur **Deploy**. La première installation prend 2 à 4 minutes.

L'application obtient une adresse du type `https://prediction-foot-v4.streamlit.app`.

## 4. Fonctionnement en production
- **Données** : elles sont retéléchargées au plus toutes les 12 heures, ou quand on clique sur le bouton « Recharger les données ». Le modèle est alors réentraîné automatiquement.
- **Mémoire** : environ 250 Mo pour l'affichage ; environ 1,1 Go pendant un recalcul (secours) ou dans le Laboratoire.
- **Mise en veille** : l'application s'endort après quelques jours sans visite. Le premier visiteur la réveille en environ 1 minute.
- **Mise à jour du code** : chaque `git push` sur `main` redéploie l'application automatiquement.
- **Suivi des prédictions** : le disque de Streamlit Cloud n'est pas permanent. Pour le suivi hebdomadaire officiel, télécharge le CSV de la page « Prédire une journée », ou utilise le notebook 04, qui enregistre le journal sur Google Drive.

## 5. Problèmes fréquents

| Symptôme | Solution |
|---|---|
| `ModuleNotFoundError: footpred` | Vérifier que `app.py` est à la racine du dépôt, à côté du dossier `footpred/` |
| Erreur de mémoire | Redémarrer l'application (menu ⋮ → Reboot) ; le chargement se limite déjà aux colonnes utiles |
| Données anciennes | Le dataset source est mis à jour avec quelques jours de décalage : cliquer sur « Recharger les données » |
| Équipe absente de la liste | La liste contient les équipes de la saison en cours (et de la saison précédente en début de saison) |
