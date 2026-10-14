"""Données en temps réel : calendrier, statuts et scores des matchs via l'API football-data.org (v4, offre gratuite).

Clé gratuite : https://www.football-data.org/client/register  → variable d'environnement FOOTBALL_DATA_API_KEY.
L'offre gratuite couvre Premier League, LaLiga, Serie A, Bundesliga, Ligue 1 et Ligue des champions (10 requêtes/minute).
Sans clé, le pipeline bascule automatiquement en mode démonstration.
"""
import json
import os
import time
import urllib.request
from datetime import date, datetime, timezone

from .equipes import PAR_FD, associer

API = "https://api.football-data.org/v4"
GRATUIT = {"PL", "PD", "SA", "BL1", "FL1", "CL"}          # compétitions de l'offre gratuite utilisées par le site
STATUTS = {"SCHEDULED": "scheduled", "TIMED": "scheduled", "IN_PLAY": "live", "PAUSED": "halftime", "FINISHED": "finished",
           "AWARDED": "finished", "POSTPONED": "postponed", "SUSPENDED": "postponed", "CANCELLED": "cancelled"}


def cle() -> str | None:
    return os.environ.get("FOOTBALL_DATA_API_KEY") or None


def _get(chemin: str, params: dict, key: str, essais: int = 3) -> dict:
    url = f"{API}{chemin}?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, headers={"X-Auth-Token": key})
    for i in range(essais):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < essais - 1:          # limite de 10 requêtes/minute
                time.sleep(7); continue
            raise


def matchs_api(debut: date, fin: date, key: str) -> list[dict]:
    """Tous les matchs des compétitions couvertes entre deux dates (incluses)."""
    comps = ",".join(c for c in PAR_FD if c in GRATUIT)
    return _get("/matches", {"competitions": comps, "dateFrom": debut.isoformat(), "dateTo": fin.isoformat()}, key).get("matches", [])


def convertir(m: dict, equipes_par_ligue: dict[str, list[str]], toutes: list[str]) -> dict | None:
    """Match football-data.org → format interne. Renvoie None si la compétition n'est pas suivie."""
    comp = PAR_FD.get(m.get("competition", {}).get("code"))
    if comp is None:
        return None
    cands = equipes_par_ligue.get(comp["code"], toutes)
    h = associer(m["homeTeam"].get("name") or "", cands) or associer(m["homeTeam"].get("shortName") or "", toutes)
    a = associer(m["awayTeam"].get("name") or "", cands) or associer(m["awayTeam"].get("shortName") or "", toutes)
    ft, ht = m.get("score", {}).get("fullTime", {}), m.get("score", {}).get("halfTime", {})
    statut = STATUTS.get(m.get("status"), "scheduled")
    return {"id": f"fd-{m['id']}", "competition": comp["code"], "kickoff": m["utcDate"], "status": statut,
            "minute": m.get("minute"), "venue": m.get("venue"), "matchday": m.get("matchday"),
            "home_api": m["homeTeam"].get("name"), "away_api": m["awayTeam"].get("name"), "home": h, "away": a,
            "score": {"home": ft.get("home"), "away": ft.get("away")} if ft.get("home") is not None else None,
            "halftime": {"home": ht.get("home"), "away": ht.get("away")} if ht.get("home") is not None else None}


def resultats_recents(depuis: date, key: str, equipes_par_ligue, toutes) -> list[dict]:
    """Matchs terminés depuis une date : sert à compléter le dataset (qui a quelques jours de retard) pour les ratings."""
    out = []
    for m in matchs_api(depuis, datetime.now(timezone.utc).date(), key):
        c = convertir(m, equipes_par_ligue, toutes)
        if c and c["status"] == "finished" and c["home"] and c["away"] and c["competition"] in ("E0", "SP1", "I1", "D1", "F1"):
            out.append(c)
    return out
