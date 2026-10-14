"""Accès aux données publiées par le pipeline (web/data/*.json), les mêmes que le site Goalgebra, et mise à jour automatique.

Deux sources de fichiers, la plus récente est affichée :
  - web/data dans le dépôt, publié toutes les 2 heures par GitHub Actions (python -m footpred.web) ;
  - un dossier temporaire du serveur Streamlit, recalculé par l'application elle-même dès que les données ont plus de
    MAJ_HEURES heures (ou sur le bouton « Mettre à jour »). Le calcul tourne en arrière-plan, dans un processus séparé
    (matchs du jour depuis football-data.org / football-data.co.uk / openfootball, puis modèle statistique v5) :
    l'application reste utilisable pendant ce temps avec les données précédentes.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import streamlit as st

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOSSIER_DEPOT = os.environ.get("GOALGEBRA_DATA_DIR") or os.path.join(RACINE, "web", "data")   # serveur : volume partagé avec le worker
PLATEFORME = os.environ.get("GOALGEBRA_PLATEFORME", "0") == "1"
DOSSIER_SERVEUR = os.path.join(tempfile.gettempdir(), "goalgebra_data")
MAJ_HEURES = 6            # au-delà, l'application relance le calcul d'elle-même (secours si GitHub Actions n'a pas publié)
PARIS = ZoneInfo("Europe/Paris")
ORDRE = ["champions-league", "europa-league", "conference-league", "premier-league", "laliga", "serie-a", "bundesliga", "ligue-1"]


def _meta(dossier):
    try:
        with open(os.path.join(dossier, "meta.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _date(iso):
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return datetime(2000, 1, 1, tzinfo=timezone.utc)


def dossier_actif() -> str:
    """Le dossier dont les données sont les plus fraîches (un rejeu compte comme le plus ancien)."""
    def cle(d):
        m = _meta(d)
        if not m:
            return (-1, datetime(2000, 1, 1, tzinfo=timezone.utc))
        return (0 if m.get("mode") == "replay" else 1, _date(m.get("generatedAt")))
    embarque = os.path.join(RACINE, "web", "data")           # données livrées avec le code (premier démarrage d'un serveur)
    return max(dict.fromkeys([DOSSIER_DEPOT, DOSSIER_SERVEUR, embarque]), key=cle)


def _lire(dossier, nom, defaut=None):
    chemin = os.path.join(dossier, nom)
    if not os.path.exists(chemin):
        return defaut
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=timedelta(hours=6), show_spinner=False, max_entries=4)
def _charger(dossier: str, tampon: float) -> dict:
    meta = _lire(dossier, "meta.json", {})
    comps = sorted(_lire(dossier, "competitions.json", []), key=lambda c: ORDRE.index(c["slug"]) if c["slug"] in ORDRE else 99)
    teams = _lire(dossier, "teams.json", [])
    index = _lire(dossier, "team-index.json", {})
    matches = sorted(_lire(dossier, "matches.json", []), key=lambda m: m["kickoff"])
    return {"meta": meta, "competitions": comps, "comp": {c["slug"]: c for c in comps}, "teams": {t["slug"]: t for t in teams},
            "index": index, "matches": matches, "match": {m["slug"]: m for m in matches}, "standings": _lire(dossier, "standings.json", {}),
            "performance": _lire(dossier, "performance.json", {}), "days": _lire(dossier, "days.json", {}),
            "markets": _lire(dossier, "markets.json", {"rows": [], "tiers": None}), "selections": _lire(dossier, "selections.json", {}),
            "journal": _lire(dossier, "journal.json", {})}


def tout() -> dict:
    d = dossier_actif()
    try:
        tampon = os.path.getmtime(os.path.join(d, "meta.json"))
    except OSError:
        tampon = 0.0
    return _charger(d, tampon)


# ---------------------------------------------------------------- mise à jour en arrière-plan
@st.cache_resource
def _etat() -> dict:
    """État partagé par toutes les sessions du serveur : un seul calcul à la fois."""
    return {"fil": None, "debut": None, "fin": None, "erreur": None, "verrou": threading.Lock()}


def age_donnees() -> timedelta | None:
    m = tout()["meta"]
    if not m or m.get("mode") == "replay":
        return None                                  # rejeu : toujours à remplacer par des données du jour
    return datetime.now(timezone.utc) - _date(m.get("generatedAt"))


def auto_active() -> bool:
    """Calcul dans l'application activé par défaut ; secret GOALGEBRA_MAJ_AUTO = "0" pour s'en remettre à GitHub Actions seul.
    En mode plateforme, c'est le service « worker » qui calcule : jamais de calcul automatique dans l'application."""
    if PLATEFORME:
        return False
    v = os.environ.get("GOALGEBRA_MAJ_AUTO")
    try:
        v = str(st.secrets.get("GOALGEBRA_MAJ_AUTO", v))
    except Exception:
        pass
    return str(v).strip() not in ("0", "false", "False", "non")


def perimees() -> bool:
    a = age_donnees()
    return auto_active() and (a is None or a > timedelta(hours=MAJ_HEURES))


def _environnement() -> dict:
    env = dict(os.environ, PYTHONPATH=RACINE)
    try:                                             # secrets Streamlit Cloud (facultatifs)
        for k in ("FOOTBALL_DATA_API_KEY", "GOALGEBRA_SOURCES"):
            if k in st.secrets and st.secrets[k]:
                env[k] = str(st.secrets[k])
    except Exception:
        pass
    return env


def _calculer(etat: dict, env: dict):
    tmp = DOSSIER_SERVEUR + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    source = os.path.join(dossier_actif(), "journal.json")         # le journal des prédictions figées se poursuit
    if os.path.exists(source):
        shutil.copy(source, os.path.join(tmp, "journal.json"))
    try:
        r = subprocess.run([sys.executable, "-m", "footpred.web", "--sortie", tmp], cwd=RACINE, env=env,
                           capture_output=True, text=True, timeout=30 * 60)
        if r.returncode != 0 or not _meta(tmp):
            lignes = [l for l in (r.stderr or r.stdout or "").splitlines() if l.strip()]
            raise RuntimeError(lignes[-1] if lignes else f"code {r.returncode}")
        ancien = DOSSIER_SERVEUR + ".old"
        shutil.rmtree(ancien, ignore_errors=True)
        if os.path.exists(DOSSIER_SERVEUR):
            os.replace(DOSSIER_SERVEUR, ancien)
        os.replace(tmp, DOSSIER_SERVEUR)
        shutil.rmtree(ancien, ignore_errors=True)
        etat["erreur"] = None
    except Exception as ex:                          # les données précédentes restent affichées
        etat["erreur"] = str(ex)[:300]
    finally:
        etat["fin"] = datetime.now(timezone.utc)


def en_cours() -> bool:
    f = _etat()["fil"]
    return bool(f and f.is_alive())


def lancer_maj(force=False) -> bool:
    """Démarre le calcul si aucun n'est en cours (et, sans `force`, si le dernier essai date de plus de 30 min)."""
    etat = _etat()
    with etat["verrou"]:
        if en_cours():
            return False
        if not force and etat["fin"] and datetime.now(timezone.utc) - etat["fin"] < timedelta(minutes=30):
            return False
        etat.update(debut=datetime.now(timezone.utc), fin=None)
        if PLATEFORME:                                   # serveur : même cycle que le worker (journal en base, supervision)
            def _cycle():
                from plateforme import worker
                try:
                    etat["erreur"] = None if worker.cycle() else "échec du calcul (voir Administration)"
                finally:
                    etat["fin"] = datetime.now(timezone.utc)
            etat["fil"] = threading.Thread(target=_cycle, daemon=True)
        else:
            etat["fil"] = threading.Thread(target=_calculer, args=(etat, _environnement()), daemon=True)
        etat["fil"].start()
        return True


def etat_maj() -> dict:
    return _etat()


def maintenant() -> datetime:
    """Horloge du site : figée à la date rejouée en mode « replay », sinon l'heure réelle."""
    m = tout()["meta"]
    return datetime.fromisoformat(m["now"]) if m.get("now") else datetime.now(timezone.utc)


def jour(iso: str) -> str:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(PARIS).date().isoformat()


def heure(m: dict) -> str:
    if m.get("timeKnown") is False:
        return "--:--"
    return datetime.fromisoformat(m["kickoff"].replace("Z", "+00:00")).astimezone(PARIS).strftime("%H:%M")


def equipe(slug: str | None) -> dict:
    d = tout()
    if not slug:
        return {"name": "?", "code": "?", "color": "#888"}
    t = d["teams"].get(slug) or d["index"].get(slug) or {}
    return {"slug": slug, "name": t.get("name", slug), "code": t.get("code", slug[:3].upper()), "color": t.get("color", "#888")}


JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def date_longue(iso_jour: str) -> str:
    d = datetime.fromisoformat(iso_jour)
    return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]} {d.year}"
