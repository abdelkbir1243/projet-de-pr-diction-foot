"""Pipeline de publication pour la plateforme web : produit les fichiers JSON lus par le frontend Next.js (web/data/).

    python -m footpred.web --sortie web/data              # données du jour (sources réelles, voir footpred/sources.py)
    python -m footpred.web --rejeu 2026-08-29             # rejoue une date passée (tests, démonstration hors ligne)

Aucune donnée n'est simulée. Modes :
- « live »     : calendrier, statuts et scores de football-data.org (clé FOOTBALL_DATA_API_KEY) ;
- « fixtures » : calendrier et cotes de football-data.co.uk (sans clé), résultats réels des derniers jours ;
- « offline »  : aucune source joignable, seuls les derniers résultats connus sont affichés ;
- « replay »   : une date passée est rejouée ; le modèle ne voit que les données antérieures à cette date.
Chaque prédiction d'un match à venir est figée avant le coup d'envoi dans journal.json.
"""
import argparse
import hashlib
import json
import os
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import config as C
from . import evaluation as E
from . import live
from . import statistiques as ST
from . import analyse as AN
from . import confiance as CF
from . import coupes as CP
from . import sources as SRC
from . import openfootball as OF
from .data import charger_matchs
from .decision import classement, definitions, trois_decisions
from .equipes import COMPETITIONS, PAR_CODE, code, couleur, nom, slug
from .features import construire
from .models import ModeleComplet
from .predict import Predicteur


def ts(equipe: str) -> str:
    """Slug d'URL d'une équipe, à partir de son nom complet : « Man City » → manchester-city."""
    return slug(nom(equipe))


from .version import MODELE as VERSION, __version__  # noqa: E402
COUPES_CODES = {v[0] for v in CP.COUPES.values()}
RES = {"V": "W", "N": "D", "D": "L"}


def _r(x, n=4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


# ================================================================ données de base
def equipes_saison(D: pd.DataFrame) -> dict[str, list[str]]:
    out = {}
    for lg in C.LIGUES:
        d = D[D.Division == lg]
        s = int(d.Season.max())
        eq = set(d[d.Season == s].HomeTeam) | set(d[d.Season == s].AwayTeam)
        if len(eq) < 16:                                     # tout début de saison : compléter avec la saison précédente
            prev = d[d.Season == s - 1]
            eq |= set(prev.HomeTeam)
        out[lg] = sorted(eq)
    return out


def classement_ligue(D: pd.DataFrame, lg: str, equipes: list[str]) -> list[dict]:
    s = int(D[D.Division == lg].Season.max())
    d = D[(D.Division == lg) & (D.Season == s)].sort_values("MatchDate")
    rows = []
    for e in equipes:
        h, a = d[d.HomeTeam == e], d[d.AwayTeam == e]
        gf, ga = int(h.FTHome.sum() + a.FTAway.sum()), int(h.FTAway.sum() + a.FTHome.sum())
        w = int((h.FTHome > h.FTAway).sum() + (a.FTAway > a.FTHome).sum()); dr = int((h.FTHome == h.FTAway).sum() + (a.FTHome == a.FTAway).sum())
        n = len(h) + len(a)
        m = ST.matchs_equipe(d, e, 5) if n else None
        rows.append({"team": ts(e), "played": n, "won": w, "drawn": dr, "lost": n - w - dr, "gf": gf, "ga": ga, "gd": gf - ga,
                     "points": 3 * w + dr, "form": [RES[x] for x in m["résultat"]] if m is not None and len(m) else []})
    rows.sort(key=lambda r: (-r["points"], -r["gd"], -r["gf"], r["team"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def profil_equipe(pred: Predicteur, e: str, lg: str) -> dict:
    d = pred.d
    M = ST.matchs_equipe(d.D_all, e, None)
    last = M.tail(10)
    L = d.L[d.L.team == e].sort_values("date")
    xg = L.tail(10)
    pts = lambda m: float(((m["résultat"] == "V") * 3 + (m["résultat"] == "N")).mean()) if len(m) else None
    home, away = M[M.lieu == "dom"].tail(10), M[M.lieu == "ext"].tail(10)
    sf, sa = last["Tirs_pour"].mean(), last["Tirs_contre"].mean()

    def bloc(m):
        if not len(m):
            return None
        return {"played": len(m), "ppg": _r(pts(m), 2), "gf": _r(m["Buts marqués_pour"].mean(), 2), "ga": _r(m["Buts marqués_contre"].mean(), 2),
                "winPct": _r((m["résultat"] == "V").mean(), 3)}
    s = int(d.D[d.D.Division == lg].Season.max())
    saison = M[M.date.dt.year.isin([s, s + 1]) & (M.date >= f"{s}-07-01")]
    return {
        "slug": ts(e), "name": nom(e), "short": e, "code": code(e), "color": couleur(e), "competition": PAR_CODE[lg]["slug"],
        "country": PAR_CODE[lg]["country"], "stadium": None, "coach": None, "elo": _r(L.elo.dropna().iloc[-1], 0) if L.elo.notna().any() else None,
        "form": [RES[x] for x in last["résultat"].tail(5)],
        "lastMatches": [{"date": r.date.date().isoformat(), "opponent": ts(r.adversaire), "opponentName": nom(r.adversaire),
                         "venue": "home" if r.lieu == "dom" else "away", "gf": int(r["Buts marqués_pour"]), "ga": int(r["Buts marqués_contre"]),
                         "result": RES[r["résultat"]], "competition": PAR_CODE.get(r.Division, {}).get("slug")} for _, r in last.iloc[::-1].iterrows()],
        "stats": {
            "window": len(last), "ppg": _r(pts(last), 2), "goalsFor": _r(last["Buts marqués_pour"].mean(), 2), "goalsAgainst": _r(last["Buts marqués_contre"].mean(), 2),
            "xgFor": _r(xg.xg_f.mean(), 2), "xgAgainst": _r(xg.xg_a.mean(), 2),
            "xgProxyFor": _r(xg.xg_f.mean(), 2), "xgProxyAgainst": _r(xg.xg_a.mean(), 2), "xgSource": "xg_proxy (tirs cadrés × conversion de la ligue)", "shots": _r(sf, 1), "shotsAgainst": _r(sa, 1),
            "shotsOnTarget": _r(last["Tirs cadrés_pour"].mean(), 1), "corners": _r(last["Corners obtenus_pour"].mean(), 1),
            "cornersAgainst": _r(last["Corners obtenus_contre"].mean(), 1), "yellow": _r(last["Cartons jaunes_pour"].mean(), 2),
            "red": _r(last["Cartons rouges_pour"].mean(), 2), "fouls": _r(last["Fautes commises_pour"].mean(), 1),
            "shotShare": _r(sf / (sf + sa), 3) if sf + sa > 0 else None,
            "cleanSheetPct": _r((last["Buts marqués_contre"] == 0).mean(), 3),
            "over25Pct": _r((last["Buts marqués_pour"] + last["Buts marqués_contre"] > 2.5).mean(), 3),
            "bttsPct": _r(((last["Buts marqués_pour"] > 0) & (last["Buts marqués_contre"] > 0)).mean(), 3),
            "home": bloc(home), "away": bloc(away),
            "season": {"label": f"{s}/{(s + 1) % 100:02d}", **(bloc(saison) or {"played": 0})},
        },
        "eloHistory": [{"date": r.date.date().isoformat(), "elo": _r(r.elo, 0)} for _, r in L.dropna(subset=["elo"]).tail(40).iterrows()],
        "_radar_raw": {"attack": xg.xg_f.mean(), "defense": -xg.xg_a.mean(), "form": pts(last.tail(5)),
                       "control": sf / (sf + sa) if sf + sa > 0 else np.nan,
                       "finishing": last["Buts marqués_pour"].sum() / max(xg.xg_f.sum(), 1e-6),
                       "venueHome": pts(home), "venueAway": pts(away)},
    }


def radars(profils: list[dict]):
    """Percentiles (0-100) de chaque dimension au sein de la ligue."""
    df = pd.DataFrame({p["slug"]: p["_radar_raw"] for p in profils}).T.astype(float)
    pct = (df.rank(pct=True) * 100).round(0)
    for p in profils:
        p["radar"] = {k: _r(v, 0) for k, v in pct.loc[p["slug"]].items()}
        del p["_radar_raw"]


def h2h(D: pd.DataFrame, a: str, b: str, n: int = 10) -> dict:
    H = D[((D.HomeTeam == a) & (D.AwayTeam == b)) | ((D.HomeTeam == b) & (D.AwayTeam == a))].sort_values("MatchDate").tail(n)
    if H.empty:
        return {"matches": [], "summary": None}
    ga = np.where(H.HomeTeam == a, H.FTHome, H.FTAway); gb = np.where(H.HomeTeam == a, H.FTAway, H.FTHome)
    tot = H.FTHome + H.FTAway
    return {"matches": [{"date": r.MatchDate.date().isoformat(), "home": ts(r.HomeTeam), "away": ts(r.AwayTeam),
                         "homeGoals": int(r.FTHome), "awayGoals": int(r.FTAway), "competition": PAR_CODE.get(r.Division, {}).get("slug")}
                        for _, r in H.iloc[::-1].iterrows()],
            "summary": {"n": len(H), "homeWins": int((ga > gb).sum()), "draws": int((ga == gb).sum()), "awayWins": int((ga < gb).sum()),
                        "avgGoals": _r(tot.mean(), 2), "bttsPct": _r(((H.FTHome > 0) & (H.FTAway > 0)).mean(), 3),
                        "over25Pct": _r((tot > 2.5).mean(), 3), "cleanSheetsHome": int((gb == 0).sum()), "cleanSheetsAway": int((ga == 0).sum())}}


# ================================================================ prédiction d'un match
def synthese(r, pa, pb, dom, ext) -> str:
    p1, px, p2 = r["1"], r["X"], r["2"]
    fav, autre, pf, po = (dom, ext, p1, p2) if p1 >= p2 else (ext, dom, p2, p1)
    ecart = pf - po
    if ecart < 0.08:
        tete = f"L'analyse statistique ne dégage pas de favori clair entre {dom} et {ext}"
    else:
        force = "un net avantage" if ecart > 0.30 else ("un avantage" if ecart > 0.15 else "un léger avantage")
        sa, sb = (pa, pb) if fav == dom else (pb, pa)
        moteurs = []
        if (sa["stats"]["ppg"] or 0) - (sb["stats"]["ppg"] or 0) > 0.4:
            moteurs.append("sa forme récente")
        if (sa["elo"] or 0) - (sb["elo"] or 0) > 60:
            moteurs.append("un niveau global (Elo) supérieur")
        if (sa["stats"]["xgFor"] or 0) - (sb["stats"]["xgFor"] or 0) > 0.25:
            moteurs.append("une production offensive plus élevée")
        if (sb["stats"]["xgAgainst"] or 0) - (sa["stats"]["xgAgainst"] or 0) > 0.25:
            moteurs.append("une défense plus solide")
        lieu = pa["stats"]["home"] if fav == dom else pb["stats"]["away"]
        if lieu and (lieu["ppg"] or 0) >= 2.0:
            moteurs.append("ses performances à domicile" if fav == dom else "ses performances à l'extérieur")
        if fav == dom and not moteurs:
            moteurs.append("l'avantage du terrain")
        raison = (", principalement lié à " + " et ".join(moteurs[:2])) if moteurs else ""
        tete = f"L'analyse statistique indique {force} pour {fav}{raison}"
    inc = "reste élevé" if max(p1, px, p2) < 0.45 else ("reste toutefois significatif" if max(p1, px, p2) < 0.62 else "est plus modéré qu'à l'accoutumée")
    nul = f" Le match nul demeure une issue crédible ({px:.0%})." if px >= 0.28 else ""
    return f"{tete}. Le niveau d'incertitude {inc}.{nul}".replace(".0%", "%")


def prediction(pred: Predicteur, dom: str, ext: str, profils: dict, jour=None, cotes=None, ligne=None, comp: AN.Comparables | None = None, lg=None,
               conf: dict | None = None, brut: dict | None = None) -> dict:
    """Prédiction et analyse statistique complète d'un match.
    `ligne` (variables d'avant-match d'un match déjà joué) : prédiction hors échantillon avec un modèle des saisons précédentes."""
    r = pred.predire_ligne(ligne) if ligne is not None else pred.predire(dom, ext, jour=jour, lg=lg)
    r["dom"], r["ext"] = nom(dom), nom(ext)
    T = classement(r)
    D3 = trois_decisions(T, ["Résultat", "Double chance", "Buts", "Corners"])
    v = r["variables"]
    h, a = pred.d.L[pred.d.L.team == dom].tail(10), pred.d.L[pred.d.L.team == ext].tail(10)
    sf = lambda t, c: t[c].mean() if len(t) else np.nan
    ctrl_n, ctrl_d = sf(h, "sf") + sf(a, "sa"), sf(h, "sf") + sf(a, "sa") + sf(a, "sf") + sf(h, "sa")
    (ps, sc) = r["scores"][0]
    pa, pb = profils.get(ts(dom)), profils.get(ts(ext))
    c, j = r["corners"], r["jaunes"]
    # degré de confiance : calibration de chaque statistique + niveau du match (mesurés hors échantillon, données du jour)
    generique = {n: g for (_, n, _, _), (_, g, _, _) in zip(definitions(r["dom"], r["ext"]), definitions("Domicile", "Extérieur"))}
    P3 = np.array([r["1"], r["X"], r["2"]])
    ecart = None
    if cotes and all(cotes.get(k) for k in ("home", "draw", "away")):
        ecart = float(CF.ecart_marche(P3[None, :], np.array([[cotes["home"], cotes["draw"], cotes["away"]]], float))[0])
    k_ = r.get("contexte") or {}
    jm = min(k_.get("joues_h") if k_.get("joues_h") is not None else np.nan, k_.get("joues_a") if k_.get("joues_a") is not None else np.nan)
    fav = [r["dom"], "Match nul", r["ext"]][int(P3.argmax())]
    trust = CF.confiance_match(conf["levels"], float(P3.max()), ecart, jm, fav) if conf else None
    cal_of = lambda nm, p: CF.chercher(conf["calibration"], generique.get(nm, nm), p) if conf else None
    if brut is not None:
        M_ = r["_M"]; G = np.arange(M_.shape[0])
        brut.update({"M": M_, "x": dict(r["variables"]), "jm": jm, "odds": cotes})
        brut.update({"goals": np.bincount((G[:, None] + G[None, :]).ravel(), weights=M_.ravel()), "corners": c.get("loi"), "p": P3,
                     "o25": r["over25"], "level": trust["level"] if trust else None})
    return {
        "model": VERSION, "home": _r(r["1"]), "draw": _r(r["X"]), "away": _r(r["2"]),
        "confidence": _r(r["precision_historique"], 2), "reliability": r["fiabilite"], "endOfSeason": bool(r["fin_de_saison"]),
        "xg": {"home": _r(r["buts_dom"], 2), "away": _r(r["buts_ext"], 2), "total": _r(r["buts_dom"] + r["buts_ext"], 2)},   # compat. : λ du modèle
        "goalsLambda": {"home": _r(r["buts_dom"], 2), "away": _r(r["buts_ext"], 2), "total": _r(r["buts_dom"] + r["buts_ext"], 2)},
        "likelyScore": {"home": int(sc.split("-")[0]), "away": int(sc.split("-")[1]), "p": _r(ps, 3)},
        "topScores": [{"score": s, "p": _r(q, 3)} for q, s in r["scores"]],
        "over15": _r(r["over15"]), "over25": _r(r["over25"]), "over35": _r(r["over35"]), "btts": _r(r["btts"]),
        "cleanSheetHome": _r(r["cs_dom"]), "cleanSheetAway": _r(r["cs_ext"]), "firstHalfGoal": _r(r["but_1re_MT"]),
        "control": _r(ctrl_n / ctrl_d, 3) if np.isfinite(ctrl_n / ctrl_d) else None,
        "corners": {"total": _r(c["total"], 2), "home": _r(c["dom"], 2), "away": _r(c["ext"], 2), "over": {str(k): _r(x) for k, x in c["plus_de"].items()}},
        "cards": {"total": _r(j["total"], 2), "home": _r(j["dom"], 2), "away": _r(j["ext"], 2), "over": {str(k): _r(x) for k, x in j["plus_de"].items()},
                  "red": _r(r["rouges"]["au_moins_un"])},
        "markets": [{"family": t.famille, "market": t["marché"], "p": _r(t["probabilité"]), "tier": t.risque, "cal": cal_of(t["marché"], t["probabilité"]),
                     "key": generique.get(t["marché"], t["marché"])}
                    for _, t in T.iterrows()],
        "trust": trust,
        "decisions": [{"profile": d.profil, "market": d["marché"], "p": _r(d["probabilité"]), "tier": d.risque} for _, d in D3.iterrows()],
        "synthesis": synthese(r, pa, pb, nom(dom), nom(ext)) if pa and pb else "",
        "expected": AN.attendus(r),
        "similar": comp.chercher(v, lg or pred.d.ligue_match(dom, ext)) if comp else None,
        "context": AN.contexte(r.get("contexte"), nom(dom), nom(ext)),
        "market": AN.marche(r, cotes),
        "source": "out-of-sample" if ligne is not None else "pre-match",
    }


# ================================================================ calendrier (sources réelles uniquement)
def _iso(ts_: pd.Timestamp, heure="15:00") -> str:
    """Date sans heure (historique) → coup d'envoi indicatif 15:00 UTC."""
    return f"{ts_.date().isoformat()}T{heure}:00Z"


def matchs_historiques(raw: pd.DataFrame, debut: date, fin: date, statut_avant: date | None = None) -> list[dict]:
    """Matchs réels du dataset entre deux dates (incluses). Avec `statut_avant` (rejeu), les matchs à partir de cette date
    sont présentés « à venir » : score et statistiques masqués, cotes d'avant-match conservées."""
    d = raw[raw.Division.isin(C.LIGUES) & (raw.MatchDate.dt.date >= debut) & (raw.MatchDate.dt.date <= fin)].dropna(subset=["FTHome"])
    out = []
    for r in d.itertuples():
        futur = statut_avant is not None and r.MatchDate.date() >= statut_avant
        num = lambda x: None if pd.isna(x) else int(x)
        odds = {k: float(v) for k, v in (("home", r.OddHome), ("draw", r.OddDraw), ("away", r.OddAway), ("over25", getattr(r, "Over25", np.nan)),
                                           ("under25", getattr(r, "Under25", np.nan))) if pd.notna(v) and v > 1}
        stats = None if futur else {k: {"home": num(getattr(r, f"Home{c}", np.nan)), "away": num(getattr(r, f"Away{c}", np.nan))}
                                    for k, c in (("shots", "Shots"), ("shotsOnTarget", "Target"), ("corners", "Corners"), ("yellow", "Yellow"),
                                                 ("red", "Red"), ("fouls", "Fouls"))}
        out.append({"id": f"h-{r.MatchDate.date().isoformat()}-{ts(r.HomeTeam)}-{ts(r.AwayTeam)}", "competition": r.Division,
                    "kickoff": _iso(r.MatchDate), "status": "scheduled" if futur else "finished", "home": r.HomeTeam, "away": r.AwayTeam,
                    "venue": None, "score": None if futur else {"home": int(r.FTHome), "away": int(r.FTAway)},
                    "halftime": None if futur or pd.isna(r.HTHome) else {"home": int(r.HTHome), "away": int(r.HTAway)},
                    "stats": stats, "odds": odds or None, "timeKnown": False})
    return out


def calendrier_fdorg(pred, eq_ligue, jour0, key) -> list[dict]:
    toutes = sorted({e for v in eq_ligue.values() for e in v} | set(pred.d.L.team.unique()))
    out = []
    for m in live.matchs_api(jour0 - timedelta(days=3), jour0 + timedelta(days=7), key):
        c = live.convertir(m, eq_ligue, toutes)
        if c and ((c["home"] and c["away"]) or c["competition"] in COUPES_CODES):
            out.append(c | {"timeKnown": True})
    return out


def rattacher_cotes(cal: list[dict], fixtures: list[dict]):
    """Ajoute aux matchs du calendrier les cotes d'avant-match de football-data.co.uk (même jour, mêmes équipes)."""
    idx = {(f["kickoff"][:10], f["home"], f["away"]): f.get("odds") for f in fixtures}
    for m in cal:
        if not m.get("odds"):
            m["odds"] = idx.get((m["kickoff"][:10], m["home"], m["away"]))


def collecter(raw: pd.DataFrame, jour0: date, key: str | None) -> tuple[pd.DataFrame, str, callable, dict]:
    """Complète l'historique avec les résultats récents puis renvoie une fonction de calendrier selon les sources joignables."""
    info = {"sources": [], "resultsAdded": 0}
    try:
        raw, n = SRC.fusionner(raw, SRC.resultats_fduk(jour0))
        info["resultsAdded"] += n
        if n:
            info["sources"].append("football-data.co.uk (résultats)")
    except Exception as e:
        print("⚠ résultats football-data.co.uk indisponibles :", e)
    if key:
        try:
            raw2, n = completer_avec_api(raw, key, equipes_saison(raw[raw.Division.isin(C.LIGUES)]))
            raw, info["resultsAdded"] = raw2, info["resultsAdded"] + n
            if n:
                info["sources"].append("football-data.org (résultats)")
        except Exception as e:
            print("⚠ football-data.org indisponible :", e)
    try:                                                       # secours sans clé (GitHub) : scores manquants + calendrier
        liste = OF.matchs(raw, jour0)
        info["_of"] = liste
        raw, n = SRC.fusionner(raw, OF.resultats(raw, jour0, liste))
        info["resultsAdded"] += n
        if n:
            info["sources"].append("openfootball (résultats)")
    except Exception as e:
        print("⚠ openfootball indisponible :", e)
    return SRC.propager_elo(raw), info


def calendrier(pred, raw, eq_ligue, jour0: date, key: str | None, info: dict) -> tuple[str, list[dict]]:
    fixtures = []
    try:
        fixtures = SRC.calendrier_fduk()
    except Exception as e:
        print("⚠ calendrier football-data.co.uk indisponible :", e)
    recents = matchs_historiques(raw, jour0 - timedelta(days=3), jour0)
    for src in SRC.ordre_sources():
        if src == "footballdata_org" and key:
            try:
                cal = calendrier_fdorg(pred, eq_ligue, jour0, key)
                if cal:
                    rattacher_cotes(cal, fixtures)
                    info["sources"].append("football-data.org (calendrier, direct)")
                    return "live", cal
            except Exception as e:
                print("⚠ calendrier football-data.org indisponible :", e)
        if src == "football_data_co_uk" and fixtures:
            info["sources"].append("football-data.co.uk (calendrier, cotes)")
            vus = {(m["kickoff"][:10], m["home"], m["away"]) for m in recents}
            futurs = [f | {"timeKnown": True} for f in fixtures if (f["kickoff"][:10], f["home"], f["away"]) not in vus]
            return "fixtures", recents + futurs
        if src == "openfootball" and info.get("_of"):
            vus = {(m["kickoff"][:10], m["home"], m["away"]) for m in recents}
            futurs = [m for m in OF.calendrier(info["_of"], jour0 - timedelta(days=3), jour0 + timedelta(days=7))
                      if (m["kickoff"][:10], m["home"], m["away"]) not in vus]
            if futurs:
                rattacher_cotes(futurs, fixtures)
                info["sources"].append("openfootball (calendrier)")
                return "fixtures", recents + futurs
    # aucune source de calendrier : derniers résultats réels connus
    der = raw[raw.Division.isin(C.LIGUES)].MatchDate.max().date()
    return "offline", matchs_historiques(raw, der - timedelta(days=6), der)


# ================================================================ coupes d'Europe (modèle Elo, footpred/coupes.py)
def preparer_coupes(raw: pd.DataFrame, rejeu: date | None, cache: str | None = "data/coupes") -> dict | None:
    """Historique des coupes, Elo d'avant-match, modèle entraîné sur les matchs joués, et évaluation hors échantillon."""
    try:
        Cbrut = CP.charger(CP.telecharger(cache))
    except Exception as e:
        print("⚠ coupes d'Europe indisponibles :", e)
        return None
    if Cbrut.empty:
        return None
    Cm = Cbrut.copy()
    if rejeu is not None:                                       # rejeu : les résultats à partir de la date rejouée sont masqués
        fut = Cm.date.dt.date >= rejeu
        Cm.loc[fut, ["FTHome", "FTAway", "HTHome", "HTAway"]] = np.nan
        Cm.loc[fut, "joue"] = False
    V, etat = CP.variables(Cm, raw)
    J = V[V.joue & V.FTHome.notna()]
    if len(J) < 300:
        return None
    modele = CP.ModeleCoupe().fit(J)
    W = CP.walk_forward(V)
    W = W.assign(pmax=W[["pH", "pD", "pA"]].max(axis=1), ok=W[["pH", "pD", "pA"]].values.argmax(1) == W.y.values,
                 niveau=[CP.niveau_coupe(e) for e in W.estime])
    return {"V": V, "etat": etat, "modele": modele, "W": W, "bilan": CP.bilan(W), "levels": CF.table_niveaux(W),
            "acc": W.groupby(pd.cut(W.pmax, [0, .42, .5, .61, 1.01], right=False), observed=False).ok.mean().fillna(0.5).tolist()}


def _cle_api(V: pd.DataFrame, nom_api: str, ds: str | None) -> str:
    if ds:
        return ds
    cible = CP.canon(nom_api, "").rstrip("|")
    for k in set(V.home_key) | set(V.away_key):
        if k.split("|")[0] == cible:
            return k
    return CP.canon(nom_api, "?")


def _affiche(nom_of: str, ds: str | None) -> str:
    return CP.nom_club(nom_of, ds)


def matchs_coupes(CUP: dict, debut: date, fin: date) -> list[dict]:
    """Matchs de coupes d'Europe (openfootball) dans la fenêtre : joués (score à 90 minutes) ou à venir."""
    from zoneinfo import ZoneInfo
    V = CUP["V"]; paris = ZoneInfo("Europe/Paris")
    out = []
    for r in V[(V.date.dt.date >= debut) & (V.date.dt.date <= fin)].itertuples():
        hh, mm = (r.heure or "21:00").split(":")
        ko = datetime(r.date.year, r.date.month, r.date.day, int(hh), int(mm), tzinfo=paris).astimezone(timezone.utc)
        joue = bool(r.joue) and r.FTHome == r.FTHome
        hd = r.home_ds if isinstance(r.home_ds, str) else None
        ad = r.away_ds if isinstance(r.away_ds, str) else None
        hn, an = _affiche(r.home_of, hd), _affiche(r.away_of, ad)
        out.append({"id": f"cup-{r.coupe}-{r.date.date().isoformat()}-{slug(hn)}-{slug(an)}", "competition": r.coupe, "cup": True,
                    "kickoff": ko.isoformat().replace("+00:00", "Z"), "timeKnown": bool(r.heure), "status": "finished" if joue else "scheduled",
                    "home": hd, "away": ad, "home_key": r.home_key, "away_key": r.away_key, "home_name": hn, "away_name": an,
                    "neutre": bool(r.neutre), "tour": r.tour, "aet": bool(r.aet), "row": r.Index,
                    "score": {"home": int(r.FTHome), "away": int(r.FTAway)} if joue else None,
                    "halftime": {"home": int(r.HTHome), "away": int(r.HTAway)} if joue and r.HTHome == r.HTHome else None,
                    "venue": None, "odds": None, "stats": None})
    return out


def vers_coupe(m: dict, CUP: dict) -> dict:
    """Match de coupe venu de football-data.org : identité des clubs pour le modèle coupes."""
    V = CUP["V"]
    hn = nom(m["home"]) if m.get("home") else CP.nom_club(m.get("home_api") or "?", None)
    an = nom(m["away"]) if m.get("away") else CP.nom_club(m.get("away_api") or "?", None)
    return m | {"cup": True, "home_key": _cle_api(V, m.get("home_api") or hn, m.get("home")), "away_key": _cle_api(V, m.get("away_api") or an, m.get("away")),
                "home_name": hn, "away_name": an, "neutre": False, "tour": None, "aet": False}


def prediction_coupe(CUP: dict, m: dict, jour) -> dict:
    """Prédiction d'un match de coupe : Elo (ClubElo ou estimé) → logit 1X2 et Poisson + Dixon-Coles pour les buts."""
    V = CUP["V"]
    if m.get("row") is not None and m["status"] == "finished" and m["row"] in CUP["W"].index:      # joué : prédiction hors échantillon
        w = CUP["W"].loc[m["row"]]
        eh, ea, sh, sa = w.elo_h, w.elo_a, bool(w.est_h), bool(w.est_a)
        mod = CP.ModeleCoupe().fit(V[V.joue & V.FTHome.notna() & (V.Season < w.Season)])
        source = "out-of-sample"
    else:
        (eh, sh), (ea, sa) = CP.elo_actuel(CUP["etat"], m["home_key"], m.get("home"), jour), CP.elo_actuel(CUP["etat"], m["away_key"], m.get("away"), jour)
        mod, source = CUP["modele"], "pre-match"
    neutre = float(m.get("neutre") or 0)
    x = pd.DataFrame([{"dElo": (eh - ea) / 100, "absElo": abs(eh - ea) / 100, "neutre": neutre, "knockout": 0.0, "estime": float(sh) + float(sa)}])
    r = mod.predire(x)
    r["dom"], r["ext"] = m["home_name"], m["away_name"]
    T = classement(r)
    D3 = trois_decisions(T, ["Résultat", "Double chance", "Buts"])
    P3 = np.array([r["1"], r["X"], r["2"]])
    fav = [r["dom"], "Match nul", r["ext"]][int(P3.argmax())]
    nv = CP.niveau_coupe(float(sh) + float(sa))
    cell = next((c for c in CUP["levels"]["cells"] if c["level"] == nv and c["from"] <= P3.max() < c["to"]), None)
    facteurs = [{"label": "Modèle coupes d'Europe", "effect": "neutral", "detail": "Fondé sur l'Elo uniquement : pas de corners, cartons ni contexte"}]
    for nm_, est, e in ((m["home_name"], sh, eh), (m["away_name"], sa, ea)):
        facteurs.append({"label": f"Elo de {nm_}", "effect": "minus" if est else "plus",
                         "detail": f"{e:.0f} · " + ("estimé sur ses seuls matchs européens" if est else "ClubElo, mis à jour avec son championnat")})
    k = int(np.digitize(P3.max(), [.42, .5, .61]))
    (ps, sc) = r["scores"][0]
    ecart = eh - ea
    qui = r["dom"] if ecart > 0 else r["ext"]
    synth = (f"Écart d'Elo de {abs(ecart):.0f} points en faveur de {qui}" if abs(ecart) >= 25 else "Les deux équipes ont un niveau Elo proche") + \
            (" (terrain neutre)." if neutre else ", avant l'avantage du terrain.") + \
            f" Probabilités : {r['dom']} {P3[0]:.0%}, nul {P3[1]:.0%}, {r['ext']} {P3[2]:.0%}. Modèle simplifié pour les coupes d'Europe, évalué sur {CUP['bilan']['n']} matchs."
    return {
        "model": f"{VERSION}-coupes", "scope": "cup", "home": _r(r["1"]), "draw": _r(r["X"]), "away": _r(r["2"]),
        "confidence": _r(CUP["acc"][k], 2), "reliability": ["faible", "moyenne", "bonne", "élevée"][k], "endOfSeason": False,
        "xg": {"home": _r(r["buts_dom"], 2), "away": _r(r["buts_ext"], 2), "total": _r(r["buts_dom"] + r["buts_ext"], 2)},   # compat. : λ du modèle
        "goalsLambda": {"home": _r(r["buts_dom"], 2), "away": _r(r["buts_ext"], 2), "total": _r(r["buts_dom"] + r["buts_ext"], 2)},
        "likelyScore": {"home": int(sc.split("-")[0]), "away": int(sc.split("-")[1]), "p": _r(ps, 3)},
        "topScores": [{"score": s_, "p": _r(q, 3)} for q, s_ in r["scores"]],
        "over15": _r(r["over15"]), "over25": _r(r["over25"]), "over35": _r(r["over35"]), "btts": _r(r["btts"]),
        "cleanSheetHome": _r(r["cs_dom"]), "cleanSheetAway": _r(r["cs_ext"]), "firstHalfGoal": _r(r["but_1re_MT"]), "control": None,
        "corners": None, "cards": None,
        "markets": [{"family": t.famille, "market": t["marché"], "p": _r(t["probabilité"]), "tier": t.risque, "cal": None} for _, t in T.iterrows()],
        "decisions": [{"profile": d_.profil, "market": d_["marché"], "p": _r(d_["probabilité"]), "tier": d_.risque} for _, d_ in D3.iterrows()],
        "synthesis": synth, "expected": AN.attendus(r), "similar": None, "context": None, "market": None, "source": source,
        "elo": {"home": _r(eh, 0), "away": _r(ea, 0), "homeEstimated": sh, "awayEstimated": sa},
        "trust": {"level": nv, "label": {"B": "Moyen", "C": "Faible"}[nv], "favorite": fav, "p": _r(float(P3.max()), 4), "evidence": cell, "factors": facteurs},
        "_r": r,
    }


def h2h_coupe(CUP: dict, a: str, b: str, cles_slug: dict) -> dict:
    H = CP.h2h(CUP["V"], a, b)
    if H.empty:
        return {"matches": [], "summary": None}
    sl = lambda k, n, ds: cles_slug.get(k) or (ts(ds) if isinstance(ds, str) else slug(CP.nom_club(n, None)))
    ga = np.where(H.home_key == a, H.FTHome, H.FTAway); gb = np.where(H.home_key == a, H.FTAway, H.FTHome)
    tot = H.FTHome + H.FTAway
    comp_slug = {v[0]: v[2] for v in CP.COUPES.values()}
    return {"matches": [{"date": r.date.date().isoformat(), "home": sl(r.home_key, r.home_of, r.home_ds), "away": sl(r.away_key, r.away_of, r.away_ds),
                         "homeGoals": int(r.FTHome), "awayGoals": int(r.FTAway), "competition": comp_slug.get(r.coupe)} for r in H.iloc[::-1].itertuples()],
            "summary": {"n": len(H), "homeWins": int((ga > gb).sum()), "draws": int((ga == gb).sum()), "awayWins": int((ga < gb).sum()),
                        "avgGoals": _r(tot.mean(), 2), "bttsPct": _r(((H.FTHome > 0) & (H.FTAway > 0)).mean(), 3),
                        "over25Pct": _r((tot > 2.5).mean(), 3), "cleanSheetsHome": int((gb == 0).sum()), "cleanSheetsAway": int((ga == 0).sum())}}


def classement_phase_ligue(V: pd.DataFrame, coupe: str, saison: int, slug_de) -> list[dict]:
    """Classement de la phase de ligue (format 2024+), calculé à partir des résultats."""
    S = V[(V.coupe == coupe) & (V.Season == saison) & V.tour.str.startswith("League") & V.joue & V.FTHome.notna()]
    if S.empty:
        return []
    t = {}
    for r in S.itertuples():
        for k, gf, ga in ((r.home_key, r.FTHome, r.FTAway), (r.away_key, r.FTAway, r.FTHome)):
            x = t.setdefault(k, {"played": 0, "won": 0, "drawn": 0, "lost": 0, "gf": 0, "ga": 0, "form": []})
            x["played"] += 1; x["gf"] += int(gf); x["ga"] += int(ga)
            res = "W" if gf > ga else ("D" if gf == ga else "L")
            x[{"W": "won", "D": "drawn", "L": "lost"}[res]] += 1; x["form"].append(res)
    rows = [{"team": slug_de[k], "played": v["played"], "won": v["won"], "drawn": v["drawn"], "lost": v["lost"], "gf": v["gf"], "ga": v["ga"],
             "gd": v["gf"] - v["ga"], "points": 3 * v["won"] + v["drawn"], "form": v["form"][-5:]} for k, v in t.items()]
    rows.sort(key=lambda r: (-r["points"], -r["gd"], -r["gf"], r["team"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


# ================================================================ performances
def performances(pred: Predicteur, journal: dict) -> dict:
    X = pred.d.X
    saisons = sorted(s for s in X.Season.unique() if s >= 2025)
    te, r = E.walk_forward(X, saisons)
    y = te.y.values; P = r["P"]; n = len(y)
    Pm = E.proba_cotes(te); ok = ~np.isnan(Pm).any(1)
    base = np.bincount(y, minlength=3) / n
    pv = P.ravel(); ov = np.eye(3)[y].ravel()
    q = pd.qcut(pv, 10, labels=False, duplicates="drop")
    cal = pd.DataFrame({"p": pv, "o": ov, "b": q}).groupby("b").agg(predicted=("p", "mean"), observed=("o", "mean"), n=("p", "size"))
    df = te.assign(ll=E.log_loss(P, y), ok=P.argmax(1) == y, llm=np.where(ok, E.log_loss(np.nan_to_num(Pm, nan=1 / 3), y), np.nan),
                   brier=E.brier(P, y), mois=te.MatchDate.dt.strftime("%Y-%m"))
    mois = df.groupby("mois").agg(logLoss=("ll", "mean"), marketLogLoss=("llm", "mean"), accuracy=("ok", "mean"), brier=("brier", "mean"), n=("ll", "size"))
    hist = df.assign(pH=P[:, 0], pD=P[:, 1], pA=P[:, 2]).sort_values("MatchDate", ascending=False).head(400)
    lab = ["H", "D", "A"]
    paliers = None
    f = os.path.join(os.path.dirname(__file__), "..", "results", "tables", "decisions_2021_2026_paliers.csv")
    if os.path.exists(f):
        t = pd.read_csv(f)
        paliers = [{"tier": row.palier, "decisions": int(row["décisions"]), "predicted": _r(row["probabilité_annoncée"]), "observed": _r(row["taux_réalisé"]),
                    "returnAtOdds": _r(row["rendement_aux_cotes"])} for _, row in t.iterrows()]
    # journal en direct (mode réel) : prédictions figées avant le match
    J = [v for v in journal.values() if v.get("result")]
    live_stats = None
    if J:
        jy = np.array([lab.index(v["result"]) for v in J]); jp = np.array([[v["pH"], v["pD"], v["pA"]] for v in J])
        live_stats = {"n": len(J), "accuracy": _r(np.mean(jp.argmax(1) == jy)), "logLoss": _r(E.log_loss(jp, jy).mean()), "brier": _r(E.brier(jp, jy).mean())}
    return {
        "scope": f"Test hors échantillon {saisons[0]}/{(saisons[0] + 1) % 100:02d} → aujourd'hui (walk-forward : chaque saison prédite par un modèle entraîné sur les saisons antérieures)",
        "matches": n, "accuracy": _r(np.mean(P.argmax(1) == y)), "logLoss": _r(E.log_loss(P, y).mean()), "brier": _r(E.brier(P, y).mean()),
        "rps": _r(E.rps(P, y).mean()), "ece": _r(E.ece(P, y)),
        "baseline": {"logLoss": _r(E.log_loss(np.tile(base, (n, 1)), y).mean()), "accuracy": _r(base.max())},
        "market": {"logLoss": _r(E.log_loss(Pm[ok], y[ok]).mean()), "accuracy": _r(np.mean(Pm[ok].argmax(1) == y[ok])), "brier": _r(E.brier(Pm[ok], y[ok]).mean())},
        "calibration": [{"predicted": _r(row.predicted), "observed": _r(row.observed), "n": int(row.n)} for _, row in cal.iterrows()],
        "byMonth": [{"month": m, **{k: _r(v) for k, v in row.items() if k != "n"}, "n": int(row.n)} for m, row in mois.iterrows()],
        "tiers": paliers, "live": live_stats,
        "history": [{"date": row.MatchDate.date().isoformat(), "competition": PAR_CODE[row.Division]["slug"], "home": ts(row.HomeTeam), "away": ts(row.AwayTeam),
                     "homeName": nom(row.HomeTeam), "awayName": nom(row.AwayTeam), "pH": _r(row.pH, 3), "pD": _r(row.pD, 3), "pA": _r(row.pA, 3),
                     "predicted": lab[int(np.argmax([row.pH, row.pD, row.pA]))], "actual": lab[int(row.y)], "score": f"{int(row.FTHome)}-{int(row.FTAway)}",
                     "correct": bool(row.ok)} for _, row in hist.iterrows()],
    }


# ================================================================ export principal
def completer_avec_api(raw, key, eq_ligue):
    """Ajoute au dataset les résultats récents de football-data.org (sans statistiques détaillées) pour mettre à jour les ratings."""
    depuis = raw[raw.Division.isin(C.LIGUES)].MatchDate.max().date() + timedelta(days=1)
    if depuis > date.today():
        return raw, 0
    toutes = sorted({e for v in eq_ligue.values() for e in v})
    nouv = live.resultats_recents(depuis, key, eq_ligue, toutes)
    if not nouv:
        return raw, 0
    add = pd.DataFrame([{"Division": m["competition"], "MatchDate": pd.Timestamp(m["kickoff"][:10]), "HomeTeam": m["home"], "AwayTeam": m["away"],
                         "FTHome": m["score"]["home"], "FTAway": m["score"]["away"],
                         "FTResult": "H" if m["score"]["home"] > m["score"]["away"] else ("D" if m["score"]["home"] == m["score"]["away"] else "A"),
                         "HTHome": (m["halftime"] or {}).get("home"), "HTAway": (m["halftime"] or {}).get("away")} for m in nouv])
    return SRC.fusionner(raw, add)


def journees(matchs: list[dict], bruts: dict, conf: dict) -> dict:
    """Analyse de chaque journée (date de Paris) : attendus de la journée avec intervalles à 80 %, niveaux de confiance,
    statistiques les mieux étayées et, pour les matchs joués, bilan attendu contre observé."""
    from zoneinfo import ZoneInfo
    paris = ZoneInfo("Europe/Paris")
    par_jour = {}
    for m in matchs:
        if not m.get("prediction") or m["id"] not in bruts or "p" not in bruts[m["id"]]:
            continue
        j = datetime.fromisoformat(m["kickoff"].replace("Z", "+00:00")).astimezone(paris).date().isoformat()
        par_jour.setdefault(j, []).append(m)
    out = {}
    for j, ms in sorted(par_jour.items()):
        b = [bruts[m["id"]] for m in ms]
        P = np.array([x["p"] for x in b])
        buts = CF.convoluer([x["goals"] for x in b])
        cor = [x["corners"] for x in b if x.get("corners") is not None]
        cor_loi = CF.convoluer(cor) if cor else None
        def bloc(probas):
            loi = CF.poisson_binomiale(list(probas))
            return {"expected": _r(float(np.sum(probas)), 2), "range": CF.intervalle(loi)}
        niveaux = {k: sum(1 for x in b if x["level"] == k) for k in ("A", "B", "C")}
        # statistiques les mieux étayées : issue probable (60-92 %) dont la calibration historique a la borne basse la plus haute
        cand = []
        for m in ms:
            for k in m["prediction"].get("markets", []):
                c = k.get("cal")
                if c and 0.6 <= (k["p"] or 0) <= 0.92 and c["n"] >= 200:
                    cand.append({"match": m["slug"], "key": k.get("key"), "homeName": m["homeName"], "awayName": m["awayName"], "market": k["market"], "family": k["family"],
                                 "p": k["p"], "observed": c["observed"], "lo": c["lo"], "hi": c["hi"], "n": c["n"]})
        # classement : borne basse de l'IC (preuve la plus solide), puis probabilité ; un seul exemple par type de statistique et par match
        cand.sort(key=lambda x: (-round(x["lo"], 2), -x["p"]))
        vus, types, top = set(), set(), []
        for x in cand:
            if x["match"] not in vus and x["key"] not in types:
                top.append(x); vus.add(x["match"]); types.add(x["key"])
            if len(top) == 5:
                break
        pm = P.max(1)
        ordre = np.argsort(pm)
        resume = {"date": j, "n": len(ms), "levels": niveaux,
                  "goals": {"expected": _r(float((np.arange(len(buts)) * buts).sum()), 1), "range": CF.intervalle(buts),
                            "perMatch": _r(float((np.arange(len(buts)) * buts).sum()) / len(ms), 2)},
                  "corners": {"expected": _r(float((np.arange(len(cor_loi)) * cor_loi).sum()), 0), "range": CF.intervalle(cor_loi)} if cor_loi is not None else None,
                  "homeWins": bloc(P[:, 0]), "draws": bloc(P[:, 1]), "awayWins": bloc(P[:, 2]), "favWins": bloc(pm),
                  "over25": bloc([x["o25"] for x in b]),
                  "clearest": {"match": ms[ordre[-1]]["slug"], "label": f"{ms[ordre[-1]]['homeName']} – {ms[ordre[-1]]['awayName']}", "p": _r(float(pm[ordre[-1]]), 3)},
                  "mostOpen": {"match": ms[ordre[0]]["slug"], "label": f"{ms[ordre[0]]['homeName']} – {ms[ordre[0]]['awayName']}", "p": _r(float(pm[ordre[0]]), 3)},
                  "best": top, "result": None}
        fin = [(m, x, p) for m, x, p in zip(ms, b, P) if m["status"] == "finished" and m.get("score")]
        if fin:
            sc = np.array([[m["score"]["home"], m["score"]["away"]] for m, _, _ in fin])
            Pf = np.array([p for _, _, p in fin]); y = np.where(sc[:, 0] > sc[:, 1], 0, np.where(sc[:, 0] == sc[:, 1], 1, 2))
            resume["result"] = {"n": len(fin), "goals": int(sc.sum()), "goalsExpected": _r(float(sum((np.arange(len(x["goals"])) * x["goals"]).sum() for _, x, _ in fin)), 1),
                                "homeWins": int((y == 0).sum()), "draws": int((y == 1).sum()), "awayWins": int((y == 2).sum()),
                                "favWins": int((Pf.argmax(1) == y).sum()), "favExpected": _r(float(Pf.max(1).sum()), 2),
                                "over25": int((sc.sum(1) > 2.5).sum()), "over25Expected": _r(float(sum(x["o25"] for _, x, _ in fin)), 2),
                                "logLoss": _r(float(E.log_loss(Pf, y).mean()), 4)}
        out[j] = resume
    return out


# ================================================================ Sélection du jour (footpred/selection_prod.py)
def _compacter(sel: dict) -> dict:
    """Version enregistrée au journal (immuable avant le coup d'envoi) et affichée dans les listes."""
    c = sel["choix"]
    garde = ("cle", "marche", "famille", "p", "p_bas", "ref", "ref_source", "ecart", "info", "cote", "ev", "ev_prudente")
    return {"decision": sel["decision"], "choix": {k: c[k] for k in garde if k in c} if c else None,
            "plusProbable": {k: sel["plus_probable"][k] for k in garde if k in sel["plus_probable"]},
            "confiance": sel["confiance"], "qualite": sel["qualite"], "desaccord": sel["desaccord"], "entropie": sel["entropie"],
            "raisons": sel["raisons"], "createdAt": sel["createdAt"], "modelVersion": sel["modelVersion"], "dataVersion": sel["dataVersion"],
            "selectionId": sel["selectionId"]}


def figer_selection(journal: dict, m: dict, sel: dict, instant: datetime, mode: str) -> bool:
    """Enregistre la sélection d'avant-match au journal : seulement avant le coup d'envoi, une seule fois, jamais réécrite.
    Une prédiction live (future) sera enregistrée à part (prediction_type = live) et ne remplace jamais celle-ci."""
    if (mode in ("live", "fixtures") and m["id"] in journal and "selection" not in journal[m["id"]]
            and sel.get("predictionType", "prematch") == "prematch" and instant < _instant(m["kickoff"])):
        journal[m["id"]]["selection"] = _compacter(sel)
        return True
    return False


def selections_du_jour(d, pred, matchs, bruts, journal, instant, fraicheur, version_donnees, mode) -> dict:
    """Analyse chaque match d'avant-match ouvert, fige la sélection au journal (avant le coup d'envoi uniquement),
    et produit le résumé par jour (selections.json)."""
    from zoneinfo import ZoneInfo
    from .selection import issue
    from .selection_prod import MoteurSelection, charger_artefact
    art = charger_artefact()
    if art is None:
        return {}
    try:
        moteur = MoteurSelection(d.X, pred.modele.m1x2, art)
    except Exception as e:
        print("⚠ moteur de sélection indisponible :", e)
        return {}
    ligues = {c["slug"] for c in COMPETITIONS if c["covered"]}
    paris = ZoneInfo("Europe/Paris")
    for m in matchs:
        p, b = m.get("prediction"), bruts.get(m["id"]) or {}
        if m.get("state") == "prematch_open" and p and p.get("source") == "pre-match" and m["competition"] in ligues and "M" in b:
            try:
                sel = moteur.analyser(b["x"], b["M"], b.get("odds"), b.get("jm"), m["homeName"], m["awayName"],
                                      {"horaire": m.get("timeKnown", True), "fraicheur": not fraicheur["stale"]})
            except Exception as e:
                print("sélection impossible", m["slug"], e); continue
            sel.update(createdAt=instant.isoformat(), modelVersion=VERSION, dataVersion=version_donnees,
                       selectionId=hashlib.sha1(f"sel|{m['id']}|{instant.isoformat()}|{VERSION}".encode()).hexdigest()[:16], predictionType="prematch")
            m["selection"] = sel
            figer_selection(journal, m, sel, instant, mode)
        elif m["id"] in journal and journal[m["id"]].get("selection"):
            fig = dict(journal[m["id"]]["selection"])                     # sélection figée avant le match, évaluée si terminé
            if m["status"] == "finished" and m.get("score") and fig.get("choix"):
                fig["resultat"] = issue(fig["choix"]["cle"], m["score"]["home"], m["score"]["away"])
                journal[m["id"]]["selection"]["resultat"] = fig["resultat"]
            m["selection"] = {**fig, "fige": True}
    jours = {}
    for m in matchs:
        if not m.get("selection"):
            continue
        j = _instant(m["kickoff"]).astimezone(paris).date().isoformat()
        jours.setdefault(j, []).append(m)
    out = {}
    for j, ms in sorted(jours.items()):
        sels = [m["selection"] for m in ms]
        dec = [s["decision"] for s in sels]
        ret = [s for s in sels if s["decision"] == "retenue"]
        raisons = {}
        for s in sels:
            if s["decision"] != "retenue":
                for r in s.get("raisons", []):
                    raisons[r] = raisons.get(r, 0) + 1
        predictibles = sorted([m for m in ms if m["selection"].get("qualite", 0) >= 60], key=lambda m: m["selection"].get("entropie", 1))[:3]
        out[j] = {"date": j, "generatedAt": instant.isoformat(), "matches": len(ms), "retained": dec.count("retenue"), "prudent": dec.count("prudente"),
                  "abstentions": dec.count("abstention"), "coverage": round(dec.count("retenue") / len(ms), 4),
                  "meanConfidenceRetained": round(float(np.mean([s["confiance"] for s in ret])), 4) if ret else None,
                  "mostPredictable": [m["slug"] for m in predictibles],
                  "reasons": sorted(raisons.items(), key=lambda t: -t[1])[:4], "freshness": fraicheur,
                  "items": [{"match": m["slug"], "competition": m["competition"], "kickoff": m["kickoff"], "home": m["home"], "away": m["away"],
                             "homeName": m["homeName"], "awayName": m["awayName"], "state": m.get("state"),
                             **{k: v for k, v in (_compacter(m["selection"]) if "candidats" in m["selection"] else m["selection"]).items()}}
                            for m in sorted(ms, key=lambda m: m["kickoff"])]}
    return out


# ================================================================ honnêteté du journal
DUREE_MATCH = timedelta(minutes=135)          # au-delà du coup d'envoi + 2 h 15, un match sans score est « en attente du résultat »


def _instant(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def figeable(m: dict, p, journal: dict, maintenant: datetime, mode: str) -> bool:
    """Une prédiction n'entre au journal que si elle est calculée AVANT le coup d'envoi d'un match encore à jouer."""
    return (mode in ("live", "fixtures") and bool(p) and m["id"] not in journal and m["status"] == "scheduled"
            and m.get("timeKnown", True) and maintenant < _instant(m["kickoff"]))


ETATS = ("scheduled", "prematch_open", "live", "awaiting_result", "finished", "postponed", "cancelled")


def etat(m: dict, maintenant: datetime) -> str:
    """État publié d'un match. `prematch_open` : prédiction d'avant-match valide et consultable (coup d'envoi à venir, horaire fiable)."""
    s = m["status"]
    if s in ("finished", "postponed", "cancelled"):
        return s
    if s in ("live", "halftime"):
        return "live"
    ko = _instant(m["kickoff"])
    if ko + DUREE_MATCH < maintenant:
        return "awaiting_result"
    if ko <= maintenant:
        return "live"
    return "prematch_open" if (m.get("prediction") and m.get("timeKnown", True)) else "scheduled"


def nettoyer_journal(journal: dict) -> int:
    """Retire les entrées enregistrées au coup d'envoi ou après (madeAt ≥ kickoff). Renvoie le nombre d'entrées retirées."""
    mauvaises = [k for k, v in journal.items() if not v.get("madeAt") or not v.get("kickoff") or _instant(v["madeAt"]) >= _instant(v["kickoff"])]
    for k in mauvaises:
        del journal[k]
    return len(mauvaises)


def marches_a_venir(matchs: list[dict], paliers) -> list[dict]:
    """Tous les marchés des matchs à venir, pour la page « Marchés & risque » (du moins risqué au plus risqué)."""
    out = []
    for m in matchs:
        p = m.get("prediction")
        if not p or m["status"] != "scheduled" or m.get("awaitingResult") or m.get("started") or p.get("source") != "pre-match":
            continue
        cotes = (p.get("market") or {}).get("odds") or {}
        imp = {r["key"]: r["market"] for r in (p.get("market") or {}).get("rows", [])}
        cle = {f"Victoire {m['homeName']}": "home", "Match nul": "draw", f"Victoire {m['awayName']}": "away", "Plus de 2,5 buts": "over25"}
        for k in p["markets"]:
            if k["p"] is None or k["p"] >= 0.97:
                continue
            ck = cle.get(k["market"])
            out.append({"match": m["slug"], "kickoff": m["kickoff"], "competition": m["competition"], "home": m["home"], "away": m["away"],
                        "homeName": m["homeName"], "awayName": m["awayName"], "family": k["family"], "market": k["market"], "p": k["p"], "tier": k["tier"],
                        "fairOdds": _r(1 / k["p"], 2), "odds": cotes.get(ck) if ck else None, "marketP": imp.get(ck) if ck else None})
    out.sort(key=lambda x: -x["p"])
    return out


def exporter(sortie="web/data", source=None, jour0: date | None = None, rejeu: date | None = None):
    os.makedirs(sortie, exist_ok=True)
    key = None if rejeu else live.cle()
    raw = charger_matchs(source, cache=None)
    if rejeu:                                                   # le modèle ne voit que le passé de la date rejouée
        jour0 = rejeu
        complet, raw = raw, raw[raw.MatchDate.dt.date < rejeu].copy()
        info = {"sources": ["dataset historique (rejeu)"], "resultsAdded": 0}
    else:
        jour0 = jour0 or datetime.now(timezone.utc).date()
        raw, info = collecter(raw, jour0, key)
    date_dataset = raw[raw.Division.isin(C.LIGUES)].MatchDate.max().date()
    d = construire(raw)
    pred = Predicteur(d)
    eq_ligue = equipes_saison(d.D)
    s_cur = int(d.X.Season.max())
    pred_prec = Predicteur(d, ModeleComplet.entrainer(d.X[d.X.Season < s_cur], s_cur - 1))   # prédictions hors échantillon
    comp = AN.Comparables(d.X)
    # backtest du jour : 5 dernières saisons + saison en cours, chaque saison prédite par un modèle des saisons précédentes
    A_bt, M_bt = CF.backtest(d.X, list(range(s_cur - 5, s_cur + 1)))
    pred.calibrer_fiabilite(M_bt[["pH", "pD", "pA"]].values, M_bt.y.values)
    pred_prec.conf_acc = pred.conf_acc
    conf = {"calibration": CF.calibration_marches(A_bt), "levels": CF.table_niveaux(M_bt)}
    CUP = preparer_coupes(raw, rejeu)                           # coupes d'Europe : modèle Elo séparé

    # calendrier (les équipes promues apparaissent dans le calendrier avant leur premier match)
    if rejeu:
        mode, cal = "replay", matchs_historiques(complet, rejeu - timedelta(days=3), rejeu + timedelta(days=7), statut_avant=rejeu)
    else:
        mode, cal = calendrier(pred, raw, eq_ligue, jour0, key, info)
    if CUP:
        cal = [vers_coupe(m, CUP) if m["competition"] in COUPES_CODES else m for m in cal]
        deja = {(m["kickoff"][:10], slug(m["home_name"]), slug(m["away_name"])) for m in cal if m.get("cup")}
        for m in matchs_coupes(CUP, jour0 - timedelta(days=3), jour0 + timedelta(days=7)):
            if (m["kickoff"][:10], slug(m["home_name"]), slug(m["away_name"])) not in deja:
                cal.append(m)
        Vj = CUP["V"][CUP["V"].joue & (CUP["V"].date.dt.date < jour0)]          # repos et charge : matchs européens inclus
        d.R = pd.concat([d.R, pd.DataFrame({"MatchDate": Vj.date.values, "HomeTeam": Vj.home_ds.fillna(Vj.home_key).values,
                                            "AwayTeam": Vj.away_ds.fillna(Vj.away_key).values})], ignore_index=True)
    else:
        cal = [m for m in cal if m["competition"] not in COUPES_CODES or (m.get("home") and m.get("away"))]
    for m in cal:
        if m["competition"] in eq_ligue:
            for e in (m["home"], m["away"]):
                if e and e not in eq_ligue[m["competition"]] and (d.L.team == e).any():
                    eq_ligue[m["competition"]].append(e)

    # équipes, classements, compétitions
    profils, standings = {}, {}
    for lg, eqs in eq_ligue.items():
        ps = [profil_equipe(pred, e, lg) for e in eqs]
        radars(ps)
        profils |= {p["slug"]: p for p in ps}
        standings[PAR_CODE[lg]["slug"]] = classement_ligue(d.D, lg, eqs)
        for row in standings[PAR_CODE[lg]["slug"]]:
            profils[row["team"]]["rank"] = row["rank"]; profils[row["team"]]["points"] = row["points"]
    competitions = []
    for c in COMPETITIONS:
        n_eq = len(eq_ligue.get(c["code"], []))
        s = int(d.D[d.D.Division == c["code"]].Season.max()) if c["covered"] else None
        stats = None
        if c["covered"]:
            x = d.D[(d.D.Division == c["code"]) & (d.D.Season == s)]
            x = x if len(x) >= 30 else d.D[d.D.Division == c["code"]].tail(380)
            stats = {"matches": len(x), "goalsPerMatch": _r((x.FTHome + x.FTAway).mean(), 2), "homeWinPct": _r((x.FTHome > x.FTAway).mean(), 3),
                     "drawPct": _r((x.FTHome == x.FTAway).mean(), 3), "awayWinPct": _r((x.FTHome < x.FTAway).mean(), 3),
                     "over25Pct": _r((x.FTHome + x.FTAway > 2.5).mean(), 3), "bttsPct": _r(((x.FTHome > 0) & (x.FTAway > 0)).mean(), 3),
                     "cornersPerMatch": _r((x.HomeCorners + x.AwayCorners).mean(), 2), "yellowPerMatch": _r((x.HomeYellow + x.AwayYellow).mean(), 2)}
        model = "league" if c["covered"] else None
        if c.get("model") == "cup" and CUP:
            V = CUP["V"]; sc = int(V[V.coupe == c["code"]].Season.max()) if (V.coupe == c["code"]).any() else None
            if sc is not None:
                model, s = "cup", sc
                x = V[(V.coupe == c["code"]) & (V.Season == sc)]
                n_eq = len(set(x.home_key) | set(x.away_key))
                x = x[x.joue & x.FTHome.notna()]
                if len(x) >= 10:
                    stats = {"matches": len(x), "goalsPerMatch": _r((x.FTHome + x.FTAway).mean(), 2), "homeWinPct": _r((x.FTHome > x.FTAway).mean(), 3),
                             "drawPct": _r((x.FTHome == x.FTAway).mean(), 3), "awayWinPct": _r((x.FTHome < x.FTAway).mean(), 3),
                             "over25Pct": _r((x.FTHome + x.FTAway > 2.5).mean(), 3), "bttsPct": _r(((x.FTHome > 0) & (x.FTAway > 0)).mean(), 3),
                             "cornersPerMatch": None, "yellowPerMatch": None}
        competitions.append({"slug": c["slug"], "code": c["code"], "name": c["name"], "country": c["country"], "cc": c["cc"], "covered": c["covered"],
                             "model": model, "zones": c["zones"], "season": f"{s}/{(s + 1) % 100:02d}" if s else None,
                             "teams": [ts(e) for e in eq_ligue.get(c["code"], [])], "nTeams": n_eq, "stats": stats,
                             "seasonCurrent": (s is None) or s >= (jour0.year if jour0.month >= 7 else jour0.year - 1)})

    journal_f = os.path.join(sortie, "journal.json")
    journal = json.load(open(journal_f)) if os.path.exists(journal_f) and mode != "replay" else {}
    retires = nettoyer_journal(journal)                          # entrées invalides d'anciennes versions
    instant = (datetime.combine(rejeu, datetime.min.time()).replace(hour=12, tzinfo=timezone.utc) if rejeu else datetime.now(timezone.utc))
    lignes = {(r.MatchDate.date().isoformat(), r.HomeTeam, r.AwayTeam): r for r in d.X[d.X.Season == s_cur].itertuples(index=False)} if len(d.X) else {}
    cols_X = list(d.X.columns)
    matchs, bruts, cles_slug, noms_cup = [], {}, {}, {}
    for m in cal:
        h, a = m["home"], m["away"]
        couvert = PAR_CODE[m["competition"]]["covered"] and ts(h) in profils and ts(a) in profils
        p = None
        commence = m["status"] == "scheduled" and _instant(m["kickoff"]) <= instant          # coup d'envoi passé, aucun score connu
        attente = commence and _instant(m["kickoff"]) + DUREE_MATCH < instant
        try:
            if m.get("cup") and not commence:
                p = prediction_coupe(CUP, m, m["kickoff"][:10])
                r_ = p.pop("_r"); M_ = r_["_M"]; G_ = np.arange(M_.shape[0])
                bruts[m["id"]] = {"goals": np.bincount((G_[:, None] + G_[None, :]).ravel(), weights=M_.ravel()), "corners": None,
                                  "p": np.array([r_["1"], r_["X"], r_["2"]]), "o25": r_["over25"], "level": p["trust"]["level"]}
            elif couvert and m["status"] in ("scheduled", "postponed") and not commence:
                p = prediction(pred, h, a, profils, jour=m["kickoff"][:10], cotes=m.get("odds"), comp=comp, lg=m["competition"], conf=conf, brut=bruts.setdefault(m["id"], {}))
            elif couvert and m["status"] == "finished" and (m["kickoff"][:10], h, a) in lignes:
                ligne = pd.Series(lignes[(m["kickoff"][:10], h, a)], index=cols_X)
                p = prediction(pred_prec, h, a, profils, cotes=m.get("odds"), ligne=ligne, comp=comp, conf=conf, brut=bruts.setdefault(m["id"], {}))
        except Exception as e:
            print("prédiction impossible", h, a, e)
        if figeable(m, p, journal, instant, mode):
            journal[m["id"]] = {"madeAt": datetime.now(timezone.utc).isoformat(), "kickoff": m["kickoff"],
                                "home": ts(h) if h else slug(m.get("home_name", "")), "away": ts(a) if a else slug(m.get("away_name", "")),
                                "pH": p["home"], "pD": p["draw"], "pA": p["away"], "model": VERSION, "predictionType": "prematch",
                                "dataVersion": f"{date_dataset.isoformat()}+{info.get('resultsAdded', 0)}",
                                "prediction": {k: v for k, v in p.items() if k != "markets"}}
        if m["id"] in journal and m["status"] == "finished" and m.get("score"):
            s_ = m["score"]; journal[m["id"]]["result"] = "H" if s_["home"] > s_["away"] else ("D" if s_["home"] == s_["away"] else "A")
            journal[m["id"]]["score"] = f"{s_['home']}-{s_['away']}"
        if m["id"] in journal and (m["status"] not in ("scheduled", "postponed") or commence):   # prédiction affichée = celle figée avant le match
            fig = journal[m["id"]]
            p = {**(fig.get("prediction") or p or {}), "home": fig["pH"], "draw": fig["pD"], "away": fig["pA"], "frozenAt": fig["madeAt"],
                 "markets": [], "source": "frozen"}
        if m.get("cup"):
            hs, as_ = (ts(h) if h else slug(m["home_name"])), (ts(a) if a else slug(m["away_name"]))
            cles_slug[m["home_key"]], cles_slug[m["away_key"]] = hs, as_
            noms_cup[hs], noms_cup[as_] = m["home_name"], m["away_name"]
            matchs.append({"id": m["id"], "slug": f"{hs}-vs-{as_}", "competition": PAR_CODE[m["competition"]]["slug"], "kickoff": m["kickoff"],
                           "timeKnown": m.get("timeKnown", True), "status": m["status"], "minute": m.get("minute"), "venue": m.get("venue"),
                           "home": hs, "away": as_, "homeName": m["home_name"], "awayName": m["away_name"], "score": m.get("score"),
                           "halftime": m.get("halftime"), "stats": None, "odds": m.get("odds"), "prediction": p, "round": m.get("tour"),
                           "extraTime": m.get("aet", False), "h2h": h2h_coupe(CUP, m["home_key"], m["away_key"], cles_slug),
                           "started": commence, "awaitingResult": attente})
            continue
        hs, as_ = ts(h), ts(a)
        matchs.append({"id": m["id"], "slug": f"{hs}-vs-{as_}", "competition": PAR_CODE[m["competition"]]["slug"], "kickoff": m["kickoff"],
                       "timeKnown": m.get("timeKnown", True), "status": m["status"], "minute": m.get("minute"), "venue": m.get("venue"),
                       "home": hs, "away": as_, "homeName": nom(h), "awayName": nom(a), "score": m.get("score"), "halftime": m.get("halftime"),
                       "stats": m.get("stats"), "odds": m.get("odds"), "prediction": p, "h2h": h2h(d.D, h, a),
                       "started": commence, "awaitingResult": attente})
    version_donnees = f"{date_dataset.isoformat()}+{info.get('resultsAdded', 0)}"
    for m in matchs:                                      # état et traçabilité de chaque prédiction
        m["state"] = etat(m, instant)
        p = m.get("prediction")
        if not p:
            continue
        if p.get("source") == "frozen":
            fig = journal.get(m["id"], {})
            p.update(predictionType="prematch", createdAt=fig.get("madeAt"), modelVersion=fig.get("model"), dataVersion=fig.get("dataVersion"))
        elif p.get("source") == "out-of-sample":
            p.update(predictionType="backtest", createdAt=None, modelVersion=VERSION, dataVersion=version_donnees)
        else:
            p.update(predictionType="prematch", createdAt=instant.isoformat(), modelVersion=VERSION, dataVersion=version_donnees)
        p["predictionId"] = hashlib.sha1(f"{m['id']}|{p.get('createdAt')}|{p.get('modelVersion')}".encode()).hexdigest()[:16]
    vus = {}
    for m in matchs:                                      # URL courte (/match/manchester-city-vs-arsenal), datée seulement si doublon
        vus[m["slug"]] = vus.get(m["slug"], 0) + 1
    for m in matchs:
        if vus[m["slug"]] > 1:
            m["slug"] = f"{m['slug']}-{m['kickoff'][:10]}"
    perf = performances(pred, journal)
    perf["confidence"] = conf["levels"]
    perf["families"] = CF.resume_familles(A_bt)
    perf["byDay"] = CF.suivi_jours(M_bt)
    perf["backtest"] = {"matches": int(len(M_bt)), "markets": int(len(A_bt)), "seasons": [int(s_cur - 5), int(s_cur)],
                        "lastDate": M_bt.date.max().date().isoformat() if len(M_bt) else None}
    if CUP:
        b = CUP["bilan"]
        perf["cups"] = {"matches": b["n"], "logLoss": _r(b["logLoss"]), "baseline": _r(b["baseline"]), "accuracy": _r(b["accuracy"]),
                        "brier": _r(b["brier"]), "ece": _r(b["ece"]), "byCup": {k: {kk: _r(vv) for kk, vv in v.items()} for k, v in b["parCoupe"].items()},
                        "levels": CUP["levels"]["levels"]}
        V = CUP["V"]                                          # phase de ligue (format 2024+) : classement calculé
        for k in set(V.home_key) | set(V.away_key):
            if k not in cles_slug:
                r0 = V[V.home_key == k].iloc[0] if (V.home_key == k).any() else V[V.away_key == k].iloc[0]
                nm_ = CP.nom_club(r0.home_of, r0.home_ds) if r0.home_key == k else CP.nom_club(r0.away_of, r0.away_ds)
                ds_ = r0.home_ds if r0.home_key == k else r0.away_ds
                cles_slug[k] = ts(ds_) if isinstance(ds_, str) else slug(nm_); noms_cup.setdefault(cles_slug[k], nm_)
        for c in competitions:
            if c.get("model") == "cup" and c["season"]:
                rows = classement_phase_ligue(V, c["code"], int(c["season"][:4]), cles_slug)
                if rows:
                    standings[c["slug"]] = rows
    jours_ = journees(matchs, bruts, conf)
    maintenant = datetime.combine(rejeu, datetime.min.time()).replace(hour=12, tzinfo=timezone.utc) if rejeu else datetime.now(timezone.utc)
    ligues = {c["slug"] for c in COMPETITIONS if c["covered"]}
    manquants = [m for m in matchs if m["awaitingResult"] and m["competition"] in ligues and _instant(m["kickoff"]) < instant - timedelta(hours=36)]
    passes = [_instant(m["kickoff"]).date() for m in matchs if m["competition"] in ligues and m["status"] == "finished"]
    passes += [_instant(m["kickoff"]).date() for m in manquants]
    retard = (max(passes) - date_dataset).days if passes else 0
    fraicheur = {"lastResult": date_dataset.isoformat(), "missingResults": len(manquants), "lagDays": max(retard, 0),
                 "stale": bool(manquants) or retard > 3, "journalRemoved": retires}
    selections = selections_du_jour(d, pred, matchs, bruts, journal, instant, fraicheur, version_donnees, mode)
    meta = {"generatedAt": datetime.now(timezone.utc).isoformat(), "dataAsOf": date_dataset.isoformat(), "resultsAddedFromApi": info["resultsAdded"],
            "freshness": fraicheur,
            "mode": mode, "referenceDate": jour0.isoformat(), "now": maintenant.isoformat() if rejeu else None, "model": VERSION,
            "sources": info["sources"], "liveScores": mode == "live"}
    recents = d.D[d.D.Season >= int(d.D.Season.max()) - 12]
    index = {ts(e): {"name": nom(e), "short": e, "code": code(e), "color": couleur(e)} for e in sorted(set(recents.HomeTeam) | set(recents.AwayTeam))}
    for sl, nm_ in noms_cup.items():                          # clubs des coupes d'Europe hors des 5 championnats : nom et écusson générique
        index.setdefault(sl, {"name": nm_, "short": nm_, "code": code(nm_), "color": couleur(nm_)})
    fichiers = {"meta.json": meta, "team-index.json": index, "competitions.json": competitions, "teams.json": list(profils.values()), "standings.json": standings,
                "matches.json": matchs, "performance.json": perf, "markets.json": {"rows": marches_a_venir(matchs, perf.get("tiers")), "tiers": perf.get("tiers")},
                "days.json": jours_, "selections.json": selections}
    if mode in ("live", "fixtures"):
        fichiers["journal.json"] = journal
    for f, obj in fichiers.items():
        with open(os.path.join(sortie, f), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"), default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"{len(matchs)} matchs · {len(profils)} équipes · mode {mode} · données au {date_dataset} (+{info['resultsAdded']} résultats récents) → {sortie}")
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sortie", default="web/data"); ap.add_argument("--source", default=None, help="chemin ou URL de Matches.csv")
    ap.add_argument("--date", default=None, help="date de référence AAAA-MM-JJ (par défaut aujourd'hui)")
    ap.add_argument("--rejeu", default=None, help="rejoue une date passée AAAA-MM-JJ avec uniquement les données antérieures")
    a = ap.parse_args()
    exporter(a.sortie, a.source, date.fromisoformat(a.date) if a.date else None, date.fromisoformat(a.rejeu) if a.rejeu else None)
