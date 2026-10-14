# Héberger Goalgebra sur un serveur (mode plateforme)

Ce guide transforme le projet en **plateforme** hébergée sur ton propre serveur : HTTPS, comptes utilisateurs, équipes suivies,
API publique avec clés et quotas, base PostgreSQL, calcul automatique des données, administration, alertes et sauvegardes.

## 1. Architecture

```
Internet ──443──▶ Caddy (HTTPS automatique, en-têtes de sécurité)
                    ├── goalgebra.ton-domaine   ──▶ app     : Streamlit (pages, comptes, administration)
                    └── api.goalgebra.ton-domaine ─▶ api    : FastAPI (API publique, clés, quotas)
                                                     worker : calcule les données toutes les 2 h (pipeline footpred)
                                                     db     : PostgreSQL (comptes, clés, journal, supervision)
                                                     sauvegarde : pg_dump quotidien (14 jours conservés)
```

- Une seule image Docker (`Dockerfile`) pour app, api et worker ; utilisateur sans privilèges, système de fichiers en lecture seule.
- Seul Caddy publie des ports (80 et 443). La base n'est jamais exposée.
- Les données calculées (`/srv/data/current`, mêmes fichiers JSON que `web/data`) sont partagées entre le worker, l'app et l'API.
- Le journal des prédictions est copié en base : une prédiction n'y entre que si elle a été faite **avant** le coup d'envoi.

## 2. Choisir un serveur

Il faut un VPS Linux (Ubuntu 24.04) avec **2 vCPU et 4 Go de RAM** au minimum : le calcul du modèle utilise environ 1,1 Go
pendant 3 à 8 minutes, toutes les 2 heures. 40 Go de disque suffisent. Les offres et les prix changent souvent : compare au
moment de commander (Hetzner, OVHcloud, Scaleway, Contabo, DigitalOcean…). Choisis un centre de données en Europe.

Il te faut aussi un **nom de domaine** (≈ 10 €/an) avec deux enregistrements DNS de type A vers l'adresse IP du serveur :
`goalgebra.ton-domaine` et `api.goalgebra.ton-domaine`.

## 3. Préparer et sécuriser le serveur (une seule fois)

Depuis ton ordinateur, crée une clé SSH si tu n'en as pas (`ssh-keygen -t ed25519`) et ajoute-la au serveur à la commande
(ou avec `ssh-copy-id root@IP`). Puis :

```bash
ssh root@IP
git clone https://github.com/<ton-compte>/projet-de-prediction-foot.git /opt/goalgebra
cd /opt/goalgebra
sudo bash deploy/installer_serveur.sh goalgebra
```

Le script : mises à jour de sécurité automatiques, pare-feu (22, 80, 443 seulement), fail2ban, Docker, utilisateur `goalgebra`,
SSH par clé uniquement et sans connexion root. **Avant de fermer ta session, vérifie dans un autre terminal** que
`ssh goalgebra@IP` fonctionne.

## 4. Configurer et lancer

```bash
ssh goalgebra@IP
sudo chown -R goalgebra:goalgebra /opt/goalgebra && cd /opt/goalgebra
cp deploy/.env.example deploy/.env
nano deploy/.env            # domaines, e-mail, mots de passe (openssl rand -base64 32 pour POSTGRES_PASSWORD)
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
docker compose -f deploy/docker-compose.yml ps          # tous les services « healthy » / « running »
```

Au premier démarrage, l'application affiche les données livrées avec le code, puis le worker les remplace par celles du jour
(3 à 8 minutes). Les certificats HTTPS sont obtenus automatiquement par Caddy.

Connecte-toi sur `https://goalgebra.ton-domaine/compte` avec `ADMIN_EMAIL` / `ADMIN_PASSWORD`, puis **change ce mot de passe**
(Mon compte → Sécurité). Le menu **Compte → Administration** apparaît pour les administrateurs.

## 5. Fonctions de la plateforme

| Fonction | Où |
|---|---|
| Inscription, connexion, déconnexion de tous les appareils | Compte → Mon compte |
| Équipes suivies (☆ Suivre sur une fiche équipe) et filtre « ★ Mes équipes » sur l'accueil | Équipes, Matchs |
| Clés d'API (5 max, quota quotidien, révocation) | Mon compte → Clés d'API |
| API publique documentée | `https://api.goalgebra.ton-domaine/docs` |
| Supervision des calculs, relance manuelle | Administration → Calculs |
| Évaluation prospective (journal 2026/27 avec résultats) | Administration → Journal prospectif |
| Gestion des comptes (désactiver, promouvoir admin) | Administration → Utilisateurs |
| Consommation de l'API, journal d'audit | Administration → API, Audit |

Exemple d'appel :

```bash
curl -H "X-API-Key: gg_…" https://api.goalgebra.ton-domaine/v1/predictions/upcoming
```

Routes : `/v1/health` (sans clé), `/v1/meta`, `/v1/competitions`, `/v1/matches?date=&competition=&team=&status=`,
`/v1/matches/{slug}`, `/v1/predictions/upcoming`, `/v1/predictions/journal`, `/v1/teams/{slug}`, `/v1/standings/{competition}`,
`/v1/performance`.

## 6. Sécurité : ce qui est en place

- **Transport** : HTTPS partout (Let's Encrypt), HSTS, redirection HTTP → HTTPS, en-têtes `nosniff`, `Referrer-Policy`,
  `Permissions-Policy`, `X-Frame-Options`.
- **Comptes** : mots de passe hachés avec bcrypt (coût 12) ; 10 caractères minimum ; 5 échecs en 15 minutes bloquent l'adresse ;
  message identique que le compte existe ou non ; sessions par cookie `SameSite=Strict; Secure`, jeton aléatoire dont seule
  l'empreinte est en base, révocables (déconnexion, changement de mot de passe, compte désactivé).
- **API** : clés aléatoires de 256 bits, seule leur empreinte SHA-256 est stockée, montrées une seule fois ; quota quotidien et
  60 requêtes/minute par clé ; erreurs internes jamais détaillées au client.
- **Conteneurs** : utilisateur sans privilèges, `no-new-privileges`, système de fichiers en lecture seule, limites de mémoire,
  base sur un réseau Docker interne.
- **Serveur** : pare-feu, fail2ban, SSH par clé uniquement, mises à jour de sécurité automatiques.
- **Application** : protection XSRF de Streamlit, téléversements désactivés, Laboratoire (réentraînement lourd) réservé aux admins.
- **Données personnelles** : seuls l'e-mail, le nom facultatif, les équipes suivies et les dates de connexion sont stockés.
  Publie une page de confidentialité (RGPD) si la plateforme est ouverte au public, et supprime un compte sur demande.

## 7. Exploitation au quotidien

```bash
cd /opt/goalgebra
docker compose -f deploy/docker-compose.yml logs -f worker          # suivre un calcul
git pull && docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build   # mettre à jour le code
ls deploy/sauvegardes/                                               # sauvegardes quotidiennes de la base
# restaurer une sauvegarde :
gunzip -c deploy/sauvegardes/goalgebra-AAAAMMJJ-HHMM.sql.gz | docker compose -f deploy/docker-compose.yml exec -T db psql -U goalgebra goalgebra
```

- **Alertes** : renseigne `ALERTE_WEBHOOK` (Discord, Slack ou ntfy) pour être prévenu d'un échec du calcul ou de données en retard.
- **Sauvegardes hors serveur** : copie régulièrement `deploy/sauvegardes/` ailleurs (rsync, stockage objet). Une sauvegarde
  qui reste sur le même disque ne protège pas d'une panne du serveur.
- **Connexion Google (facultatif)** : ajoute une section `[auth]` OIDC dans `.streamlit/secrets.toml` (voir la documentation
  Streamlit « st.login ») ; un bouton « Se connecter avec Google » apparaît, le compte est créé au premier passage.

## 8. En local, sans Docker

```bash
pip install -r requirements-plateforme.txt
export GOALGEBRA_PLATEFORME=1 COOKIE_SECURE=0 ADMIN_EMAIL=admin@exemple.fr ADMIN_PASSWORD=motdepasse123
python -m plateforme.worker --une-fois          # crée la base SQLite (data/goalgebra.db), l'admin et les données
streamlit run app.py                            # http://localhost:8501
uvicorn plateforme.api:app --port 8000          # http://localhost:8000/docs
```

Sans `GOALGEBRA_PLATEFORME=1`, l'application reste la version Streamlit Community Cloud, sans comptes ni base de données.
