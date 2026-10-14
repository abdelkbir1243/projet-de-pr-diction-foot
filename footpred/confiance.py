"""Degré de confiance des prédictions, mesuré sur des matchs que le modèle n'avait pas vus.

Trois niveaux de preuve, tous recalculés à chaque publication avec les données du jour :

1. Calibration de chaque statistique : quand le modèle annonce p pour un marché (plus de 2,5 buts, plus de 9,5 corners…),
   à quelle fréquence l'issue s'est-elle réalisée ? (intervalle de Wilson à 95 %).
2. Degré de confiance d'un match (A, B, C) : facteurs dont l'effet sur la fiabilité est démontré (docs/resultats.md §12) :
   désaccord avec les cotes et tout début de saison. Pour chaque niveau et chaque netteté du favori, on publie le taux
   de réussite observé du favori.
3. Suivi jour par jour : pour chaque date passée, buts et victoires attendus contre observés.

Le backtest utilise un modèle entraîné uniquement sur les saisons précédentes (walk-forward), saison en cours comprise :
la calibration s'actualise donc avec chaque journée jouée.
"""
import numpy as np
import pandas as pd

from . import config as C
from . import evaluation as E
from .decision import definitions
from .labo import probas_bloc
from .models import ModeleComplet

BIN = 0.05                     # largeur des classes de probabilité
N_MIN = 40                     # effectif minimal pour publier une classe
DEBUT = 4                      # moins de 4 matchs joués dans la saison : « début de saison »
ECART_B, ECART_C = 0.05, 0.10  # désaccord avec les cotes (probabilité 1X2 la plus éloignée)
NETTETE = [0, .42, .50, .61, 1.01]
NIVEAUX = {"A": "Élevé", "B": "Moyen", "C": "Faible"}


def wilson(k: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, c - h), min(1.0, c + h)


def ecart_marche(p: np.ndarray, cotes: np.ndarray) -> np.ndarray:
    """Plus grand écart absolu entre les probabilités 1X2 du modèle et celles des cotes (normalisées) ; NaN sans cotes."""
    inv = 1 / cotes
    pm = inv / inv.sum(1, keepdims=True)
    return np.abs(p - pm).max(1)


def niveau(ecart: float | None, joues_min: float | None) -> str:
    debut = joues_min is not None and not np.isnan(joues_min) and joues_min < DEBUT
    if ecart is not None and not np.isnan(ecart):
        if ecart >= ECART_C:
            return "C"
        if ecart >= ECART_B:
            return "B"
    return "B" if debut else "A"


# ---------------------------------------------------------------- backtest
def backtest(X: pd.DataFrame, saisons: list[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prédictions hors échantillon de tous les marchés. Renvoie (A : une ligne par match × marché, M : une ligne par match)."""
    besoin = sorted(set(C.FE_CORNERS + C.FE_JAUNES + C.FE_ROUGES) | {"HomeCorners", "AwayCorners", "HomeYellow", "AwayYellow", "HomeRed", "AwayRed"})
    defs = definitions("Domicile", "Extérieur")
    longs, matchs = [], []
    for s in saisons:
        TE = X[X.Season == s].dropna(subset=besoin)
        if TE.empty or (X.Season < s).sum() < 2000:
            continue
        mc = ModeleComplet.entrainer(X[X.Season < s], s - 1)
        r = probas_bloc(mc, TE)
        lh, la = mc.buts.lambdas(TE)
        for fam, nom, fp, fo in defs:
            longs.append(pd.DataFrame({"mid": TE.index, "famille": fam, "marché": nom, "p": fp(r), "réalisé": fo(TE).values}))
        P = np.c_[r["1"], r["X"], r["2"]]
        cotes = TE[["OddHome", "OddDraw", "OddAway"]].values.astype(float)
        mu_c = mc.stats.m["corners"].moyenne(TE) if mc.stats is not None else np.full(len(TE), np.nan)
        matchs.append(pd.DataFrame({
            "mid": TE.index, "date": TE.MatchDate.values, "Division": TE.Division.values, "saison": s,
            "home": TE.HomeTeam.values, "away": TE.AwayTeam.values, "pH": P[:, 0], "pD": P[:, 1], "pA": P[:, 2], "y": TE.y.values,
            "xg": lh + la, "buts": (TE.FTHome + TE.FTAway).values, "o25": r["over25"], "corners_att": mu_c,
            "corners": (TE.HomeCorners + TE.AwayCorners).values,
            "ecart": ecart_marche(P, cotes), "joues_min": np.minimum(TE.joues_h, TE.joues_a).values}))
    A = pd.concat(longs, ignore_index=True)
    M = pd.concat(matchs, ignore_index=True)
    P = M[["pH", "pD", "pA"]].values
    M["pmax"], M["fav"] = P.max(1), P.argmax(1)
    M["ok"] = M.fav == M.y
    M["niveau"] = [niveau(e, j) for e, j in zip(M.ecart, M.joues_min)]
    return A, M


# ---------------------------------------------------------------- 1. calibration de chaque statistique
def calibration_marches(A: pd.DataFrame) -> dict:
    """{marché générique: [[borne_basse, borne_haute, n, annoncé, observé, ic_bas, ic_haut], …]} par classes de 5 points."""
    A = A.assign(classe=np.minimum((A.p / BIN).astype(int), int(1 / BIN) - 1))
    out = {}
    for (nom, c), g in A.groupby(["marché", "classe"]):
        if len(g) < N_MIN:
            continue
        lo, hi = wilson(g["réalisé"].sum(), len(g))
        out.setdefault(nom, []).append([round(c * BIN, 2), round((c + 1) * BIN, 2), int(len(g)), round(g.p.mean(), 4),
                                        round(g["réalisé"].mean(), 4), round(lo, 4), round(hi, 4)])
    return out


def chercher(cal: dict, nom_generique: str, p: float) -> dict | None:
    for lo, hi, n, ann, obs, a, b in cal.get(nom_generique, []):
        if lo <= p < hi or (hi >= 1 and p >= lo):
            return {"n": n, "announced": ann, "observed": obs, "lo": a, "hi": b}
    return None


def resume_familles(A: pd.DataFrame) -> list[dict]:
    """Calibration globale par famille de statistiques (écart moyen pondéré entre annoncé et observé)."""
    A = A.assign(classe=np.minimum((A.p / BIN).astype(int), int(1 / BIN) - 1))
    out = []
    for fam, g in A.groupby("famille"):
        t = g.groupby("classe").agg(p=("p", "mean"), o=("réalisé", "mean"), n=("p", "size"))
        ece = float((t.p - t.o).abs().mul(t.n).sum() / t.n.sum())
        out.append({"family": fam, "n": int(len(g)), "ece": round(ece, 4),
                    "points": [{"announced": round(r.p, 3), "observed": round(r.o, 3), "n": int(r.n)} for r in t[t.n >= N_MIN].itertuples()]})
    return out


# ---------------------------------------------------------------- 2. degré de confiance d'un match
def table_niveaux(M: pd.DataFrame) -> dict:
    """Réussite observée du favori par niveau de confiance et par netteté du favori."""
    M = M.assign(nettete=pd.cut(M.pmax, NETTETE, right=False, labels=False))
    niveaux = {}
    for nv, g in M.groupby("niveau"):
        lo, hi = wilson(g.ok.sum(), len(g))
        P = g[["pH", "pD", "pA"]].values
        niveaux[nv] = {"label": NIVEAUX[nv], "n": int(len(g)), "announced": round(g.pmax.mean(), 4), "observed": round(g.ok.mean(), 4),
                       "lo": round(lo, 4), "hi": round(hi, 4), "logLoss": round(float(E.log_loss(P, g.y.values).mean()), 4),
                       "share": round(len(g) / len(M), 3)}
    cases = []
    for (nv, k), g in M.groupby(["niveau", "nettete"]):
        if len(g) < N_MIN:
            continue
        lo, hi = wilson(g.ok.sum(), len(g))
        cases.append({"level": nv, "from": NETTETE[k], "to": min(NETTETE[k + 1], 1.0), "n": int(len(g)), "announced": round(g.pmax.mean(), 4),
                      "observed": round(g.ok.mean(), 4), "lo": round(lo, 4), "hi": round(hi, 4)})
    return {"levels": niveaux, "cells": cases}


def confiance_match(table: dict, pmax: float, ecart: float | None, joues_min: float | None, favori: str) -> dict:
    nv = niveau(ecart, joues_min)
    cell = next((c for c in table["cells"] if c["level"] == nv and c["from"] <= pmax < c["to"]), None)
    facteurs = []
    if ecart is None or np.isnan(ecart):
        facteurs.append({"label": "Cotes indisponibles", "effect": "neutral", "detail": "Pas de comparaison possible avec le marché"})
    elif ecart >= ECART_C:
        facteurs.append({"label": "Désaccord marqué avec les cotes", "effect": "minus", "detail": f"Écart de {100 * ecart:.0f} points sur une issue 1X2"})
    elif ecart >= ECART_B:
        facteurs.append({"label": "Désaccord modéré avec les cotes", "effect": "minus", "detail": f"Écart de {100 * ecart:.0f} points sur une issue 1X2"})
    else:
        facteurs.append({"label": "Accord avec les cotes", "effect": "plus", "detail": f"Écart maximal de {100 * ecart:.0f} points"})
    if joues_min is not None and not np.isnan(joues_min) and joues_min < DEBUT:
        facteurs.append({"label": "Début de saison", "effect": "minus", "detail": f"{int(joues_min)} match(s) joué(s) : effectifs et niveaux encore incertains"})
    else:
        facteurs.append({"label": "Saison installée", "effect": "plus", "detail": "Forme et classement calculés sur assez de matchs"})
    facteurs.append({"label": "Netteté du favori", "effect": "plus" if pmax >= 0.61 else ("minus" if pmax < 0.42 else "neutral"),
                     "detail": f"{favori} à {100 * pmax:.0f} %"})
    return {"level": nv, "label": NIVEAUX[nv], "favorite": favori, "p": round(pmax, 4), "evidence": cell, "factors": facteurs}


# ---------------------------------------------------------------- 3. suivi jour par jour
def suivi_jours(M: pd.DataFrame, n_jours: int = 60) -> list[dict]:
    """Pour les dernières dates jouées : attendus (somme des prédictions) contre observés."""
    out = []
    for jour, g in M.sort_values("date").groupby(M.date.dt.date):
        out.append({"date": jour.isoformat(), "n": int(len(g)), "goalsExpected": round(float(g.xg.sum()), 1), "goals": int(g.buts.sum()),
                    "favExpected": round(float(g.pmax.sum()), 2), "favWins": int(g.ok.sum()),
                    "homeExpected": round(float(g.pH.sum()), 2), "homeWins": int((g.y == 0).sum()),
                    "drawExpected": round(float(g.pD.sum()), 2), "draws": int((g.y == 1).sum()),
                    "over25Expected": round(float(g.o25.sum()), 2), "over25": int((g.buts > 2.5).sum()),
                    "logLoss": round(float(E.log_loss(g[["pH", "pD", "pA"]].values, g.y.values).mean()), 4)})
    return out[-n_jours:]


# ---------------------------------------------------------------- résumé d'une journée à venir ou jouée
def convoluer(lois: list[np.ndarray]) -> np.ndarray:
    tot = np.array([1.0])
    for l in lois:
        tot = np.convolve(tot, l)
    return tot


def intervalle(loi: np.ndarray, niveau_: float = 0.8) -> tuple[int, int]:
    c = np.cumsum(loi / loi.sum())
    return int(np.searchsorted(c, (1 - niveau_) / 2)), int(np.searchsorted(c, 1 - (1 - niveau_) / 2))


def poisson_binomiale(p: list[float]) -> np.ndarray:
    return convoluer([np.array([1 - q, q]) for q in p]) if p else np.array([1.0])
