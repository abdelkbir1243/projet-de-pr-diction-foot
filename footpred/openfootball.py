"""Source de secours sans clé : openfootball/football.json (GitHub, domaine public).

Fournit le calendrier complet de la saison des 5 championnats (dates et heures locales) et les scores une fois saisis par
les contributeurs (souvent avec quelques jours de retard). Hébergé sur raw.githubusercontent.com, donc joignable depuis
Streamlit Cloud et GitHub Actions même quand football-data.co.uk ou football-data.org ne répondent pas.

Les noms d'équipes (« FC Bayern München ») sont ramenés à ceux du dataset (« Bayern Munich ») par equipes.associer.
"""
import json
import urllib.request
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from . import config as C
from .equipes import associer

BASE = "https://raw.githubusercontent.com/openfootball/football.json/master"
FICHIERS = {"E0": "en.1", "SP1": "es.1", "I1": "it.1", "D1": "de.1", "F1": "fr.1"}
FUSEAUX = {"E0": "Europe/London", "SP1": "Europe/Madrid", "I1": "Europe/Rome", "D1": "Europe/Berlin", "F1": "Europe/Paris"}
D2_DE = {v: k for k, v in C.DIV2.items()}


def saison(jour: date) -> str:
    s = jour.year if jour.month >= 7 else jour.year - 1
    return f"{s}-{(s + 1) % 100:02d}"


def _json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "goalgebra/1.0 (projet academique)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def _score(m: dict, cle: str):
    s = m.get("score")
    v = s.get(cle) if isinstance(s, dict) else (s if cle == "ft" else None)
    return v if isinstance(v, list) and len(v) == 2 and all(isinstance(x, int) for x in v) else None


def candidats(raw: pd.DataFrame, lg: str, jour: date) -> list[str]:
    """Équipes du championnat et de sa deuxième division sur les 3 dernières saisons (les promus y figurent)."""
    r = raw[raw.Division.isin([lg, D2_DE.get(lg, lg)]) & (raw.MatchDate >= pd.Timestamp(jour) - pd.Timedelta(days=3 * 365))]
    return sorted(set(r.HomeTeam) | set(r.AwayTeam))


def matchs(raw: pd.DataFrame, jour: date, ligues=None, telecharger=_json) -> list[dict]:
    """Tous les matchs de la saison de `jour` (joués ou non), noms ramenés au dataset. Une ligue indisponible est ignorée."""
    out = []
    for lg in ligues or C.LIGUES:
        try:
            data = telecharger(f"{BASE}/{saison(jour)}/{FICHIERS[lg]}.json")
        except Exception as e:
            print(f"⚠ openfootball {lg} :", e)
            continue
        cand, tz = candidats(raw, lg, jour), ZoneInfo(FUSEAUX[lg])
        cache = {}
        for m in data.get("matches", []):
            try:
                j = date.fromisoformat(m["date"])
            except (KeyError, ValueError):
                continue
            h, a = (cache.setdefault(n, associer(n, cand)) for n in (m.get("team1", ""), m.get("team2", "")))
            if not h or not a:
                continue
            t = m.get("time") or ""
            heure_connue = len(t) >= 4 and ":" in t
            hh, mm = (int(x) for x in t.split(":")[:2]) if heure_connue else (15, 0)
            ko = datetime(j.year, j.month, j.day, hh, mm, tzinfo=tz).astimezone(timezone.utc)
            out.append({"competition": lg, "date": j, "kickoff": ko.isoformat().replace("+00:00", "Z"), "timeKnown": heure_connue,
                        "home": h, "away": a, "ft": _score(m, "ft"), "ht": _score(m, "ht"), "round": m.get("round")})
    return out


def resultats(raw: pd.DataFrame, jour: date, liste=None) -> pd.DataFrame:
    """Matchs joués → lignes au format Matches.csv (score uniquement : pas de tirs, corners ni cotes)."""
    liste = matchs(raw, jour) if liste is None else liste
    rows = [{"Division": m["competition"], "MatchDate": pd.Timestamp(m["date"]), "HomeTeam": m["home"], "AwayTeam": m["away"],
             "FTHome": m["ft"][0], "FTAway": m["ft"][1], "FTResult": "H" if m["ft"][0] > m["ft"][1] else ("D" if m["ft"][0] == m["ft"][1] else "A"),
             "HTHome": m["ht"][0] if m["ht"] else None, "HTAway": m["ht"][1] if m["ht"] else None}
            for m in liste if m["ft"] and m["date"] <= jour]
    return pd.DataFrame(rows)


def calendrier(liste: list[dict], debut: date, fin: date) -> list[dict]:
    """Matchs entre deux dates au format du calendrier interne (web.py)."""
    out = []
    for m in liste:
        if not (debut <= m["date"] <= fin):
            continue
        fini = m["ft"] is not None
        out.append({"id": f"of-{m['date'].isoformat()}-{m['home']}-{m['away']}".replace(" ", "_"), "competition": m["competition"],
                    "kickoff": m["kickoff"], "timeKnown": m["timeKnown"], "status": "finished" if fini else "scheduled",
                    "home": m["home"], "away": m["away"], "venue": None,
                    "score": {"home": m["ft"][0], "away": m["ft"][1]} if fini else None,
                    "halftime": {"home": m["ht"][0], "away": m["ht"][1]} if fini and m["ht"] else None,
                    "stats": None, "odds": None, "source": "openfootball"})
    return out
