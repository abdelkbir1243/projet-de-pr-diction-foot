"""Sources de données réelles, interchangeables. Aucune donnée n'est simulée.

| Source                     | Clé      | Fournit                                                                  |
|----------------------------|----------|--------------------------------------------------------------------------|
| football-data.co.uk        | aucune   | résultats de la saison en cours (avec tirs, corners, cartons, cotes) ;   |
|                            |          | calendrier des prochains jours avec les cotes d'avant-match (fixtures)   |
| football-data.org          | gratuite | calendrier, statuts et scores en direct (footpred/live.py)               |
| dataset xgabora (GitHub)   | aucune   | historique 2000 → aujourd'hui (quelques semaines de retard)              |
| openfootball (GitHub)      | aucune   | calendrier complet de la saison, scores (quelques jours de retard)       |

Ordre d'utilisation (variable GOALGEBRA_SOURCES, par défaut « footballdata_org,football_data_co_uk,openfootball ») :
le calendrier vient de la première source disponible ; les cotes sont toujours rattachées depuis football-data.co.uk.
Si une source échoue, on passe à la suivante. Si aucune ne répond, le site affiche les derniers résultats réels connus.
"""
import io
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import config as C

FDUK = "https://www.football-data.co.uk"
LONDRES = ZoneInfo("Europe/London")

# Colonnes football-data.co.uk → schéma du dataset (Matches.csv)
COLS = {"Div": "Division", "HomeTeam": "HomeTeam", "AwayTeam": "AwayTeam", "FTHG": "FTHome", "FTAG": "FTAway", "FTR": "FTResult",
        "HTHG": "HTHome", "HTAG": "HTAway", "HS": "HomeShots", "AS": "AwayShots", "HST": "HomeTarget", "AST": "AwayTarget",
        "HF": "HomeFouls", "AF": "AwayFouls", "HC": "HomeCorners", "AC": "AwayCorners", "HY": "HomeYellow", "AY": "AwayYellow",
        "HR": "HomeRed", "AR": "AwayRed", "MaxH": "MaxHome", "MaxD": "MaxDraw", "MaxA": "MaxAway", "Avg>2.5": "Over25", "Avg<2.5": "Under25"}


def ordre_sources() -> list[str]:
    brut = os.environ.get("GOALGEBRA_SOURCES") or "footballdata_org,football_data_co_uk,openfootball"   # vide = défaut
    ordre = [s.strip() for s in brut.split(",") if s.strip()]
    return ordre + ([] if "openfootball" in ordre else ["openfootball"])     # le secours GitHub reste toujours en dernier


def _telecharger(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "goalgebra/1.0 (projet academique)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8-sig", errors="replace")


def _dates(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")


def _cotes(df: pd.DataFrame) -> pd.DataFrame:
    """Cotes 1X2 : moyenne du marché si disponible, sinon Bet365."""
    out = pd.DataFrame(index=df.index)
    for k, nom in (("H", "OddHome"), ("D", "OddDraw"), ("A", "OddAway")):
        out[nom] = pd.to_numeric(df.get(f"Avg{k}", df.get(f"B365{k}")), errors="coerce")
        if f"B365{k}" in df:
            out[nom] = out[nom].fillna(pd.to_numeric(df[f"B365{k}"], errors="coerce"))
    return out


def lire_resultats_fduk(texte: str) -> pd.DataFrame:
    """CSV de saison football-data.co.uk → lignes au format Matches.csv (matchs joués uniquement)."""
    df = pd.read_csv(io.StringIO(texte))
    df = df[df.get("FTHG").notna()] if "FTHG" in df else df.iloc[0:0]
    out = df[[c for c in COLS if c in df]].rename(columns=COLS)
    out["MatchDate"] = _dates(df)
    out = out.join(_cotes(df))
    for c in out.columns:
        if c not in ("Division", "HomeTeam", "AwayTeam", "FTResult", "MatchDate"):
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out.dropna(subset=["MatchDate", "HomeTeam", "AwayTeam", "FTHome", "FTAway"]).reset_index(drop=True)


def lire_calendrier_fduk(texte: str) -> list[dict]:
    """fixtures.csv (matchs des prochains jours + cotes d'avant-match) → calendrier interne."""
    df = pd.read_csv(io.StringIO(texte))
    if df.empty:
        return []
    df = df[df.Div.isin(C.LIGUES)].copy()
    jours = _dates(df)
    cotes = _cotes(df)
    o25 = pd.to_numeric(df.get("Avg>2.5", df.get("B365>2.5")), errors="coerce")
    u25 = pd.to_numeric(df.get("Avg<2.5", df.get("B365<2.5")), errors="coerce")
    out = []
    for i, r in df.iterrows():
        if pd.isna(jours[i]):
            continue
        hh, mm = (str(r.get("Time")) if isinstance(r.get("Time"), str) else "15:00").split(":")[:2]
        local = datetime(jours[i].year, jours[i].month, jours[i].day, int(hh), int(mm), tzinfo=LONDRES)
        ko = local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        odds = {"home": cotes.at[i, "OddHome"], "draw": cotes.at[i, "OddDraw"], "away": cotes.at[i, "OddAway"],
                "over25": o25[i] if o25 is not None else np.nan, "under25": u25[i] if u25 is not None else np.nan}
        odds = {k: float(v) for k, v in odds.items() if v is not None and np.isfinite(v)}
        out.append({"id": f"fduk-{jours[i].date().isoformat()}-{r.HomeTeam}-{r.AwayTeam}".replace(" ", "_"), "competition": r.Div,
                    "kickoff": ko, "status": "scheduled", "home": r.HomeTeam, "away": r.AwayTeam, "venue": None,
                    "odds": odds or None, "source": "football-data.co.uk"})
    return out


def code_saison(jour: date) -> str:
    s = jour.year if jour.month >= 7 else jour.year - 1
    return f"{s % 100:02d}{(s + 1) % 100:02d}"


def resultats_fduk(jour: date) -> pd.DataFrame:
    """Résultats de la saison en cours des 5 ligues (avec la saison précédente en juillet-août, au cas où)."""
    parts = []
    for lg in C.LIGUES:
        try:
            parts.append(lire_resultats_fduk(_telecharger(f"{FDUK}/mmz4281/{code_saison(jour)}/{lg}.csv")))
        except Exception as e:                       # une ligue indisponible ne bloque pas les autres
            print(f"⚠ football-data.co.uk {lg} :", e)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def calendrier_fduk() -> list[dict]:
    return lire_calendrier_fduk(_telecharger(f"{FDUK}/fixtures.csv"))


# ---------------------------------------------------------------- fusion avec l'historique
ELO_K, ELO_DOM = 20.0, 65.0


def propager_elo(raw: pd.DataFrame) -> pd.DataFrame:
    """Complète l'Elo des matchs récents qui n'en ont pas (résultats ajoutés depuis une API).

    Formule Elo classique (K = 20, avantage du terrain 65 points, multiplicateur selon l'écart de buts), en partant du dernier
    Elo connu de chaque équipe. Approximation de ClubElo, utilisée uniquement pour les quelques semaines manquantes.
    """
    raw = raw.sort_values("MatchDate", kind="stable").reset_index(drop=True)
    manque = raw.HomeElo.isna() | raw.AwayElo.isna()
    if not manque.any():
        return raw
    premier = raw.index[manque][0]
    elo = {}
    # Elo après chaque match connu (Elo d'avant-match + mise à jour), puis propagation sur les lignes sans Elo
    for i in raw.index[max(0, premier - 50_000):]:                   # ~2 saisons toutes divisions : dernier Elo de chaque équipe
        h, a, gh, ga = raw.at[i, "HomeTeam"], raw.at[i, "AwayTeam"], raw.at[i, "FTHome"], raw.at[i, "FTAway"]
        eh = raw.at[i, "HomeElo"] if pd.notna(raw.at[i, "HomeElo"]) else elo.get(h)
        ea = raw.at[i, "AwayElo"] if pd.notna(raw.at[i, "AwayElo"]) else elo.get(a)
        if eh is None or ea is None or pd.isna(gh) or pd.isna(ga):
            continue
        raw.at[i, "HomeElo"], raw.at[i, "AwayElo"] = eh, ea
        attendu = 1 / (1 + 10 ** (-(eh + ELO_DOM - ea) / 400))
        s = 1.0 if gh > ga else (0.5 if gh == ga else 0.0)
        mult = 1 if abs(gh - ga) <= 1 else (1.5 if abs(gh - ga) == 2 else (11 + abs(gh - ga)) / 8)
        delta = ELO_K * mult * (s - attendu)
        elo[h], elo[a] = eh + delta, ea - delta
    return raw


def fusionner(raw: pd.DataFrame, recents: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Ajoute à l'historique les résultats plus récents que sa dernière date (sans doublons), puis complète l'Elo."""
    if recents is None or recents.empty:
        return raw, 0
    cle = lambda df: df.MatchDate.dt.strftime("%Y-%m-%d") + "|" + df.HomeTeam + "|" + df.AwayTeam
    nouv = recents[~cle(recents).isin(set(cle(raw)))]
    nouv = nouv[nouv.MatchDate >= raw[raw.Division.isin(C.LIGUES)].MatchDate.max() - timedelta(days=10)]
    if nouv.empty:
        return raw, 0
    nouv = nouv.assign(Season=np.where(nouv.MatchDate.dt.month >= 7, nouv.MatchDate.dt.year, nouv.MatchDate.dt.year - 1))
    out = pd.concat([raw, nouv], ignore_index=True)
    return propager_elo(out), len(nouv)
