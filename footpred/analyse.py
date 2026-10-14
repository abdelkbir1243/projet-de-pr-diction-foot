"""Analyse statistique d'un match à venir : statistiques attendues avec intervalles, matchs comparables de l'historique,
contexte (repos, enjeu, statut) et comparaison avec les probabilités implicites des cotes.

L'objectif est de décrire ce qui est statistiquement plausible, pas de désigner un « pari » : la section v5 de
docs/resultats.md montre que le marché contient toute l'information du modèle (poids optimal du modèle ≈ 0 dans une
combinaison modèle + cotes).
"""
import numpy as np
import pandas as pd

from . import contexte as K
from .markets import shin


def _r(x, n=3):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


# ---------------------------------------------------------------- intervalles
def intervalle(loi: np.ndarray, niveau: float = 0.8) -> tuple[int, int]:
    """Plus petit intervalle central [a, b] d'une loi discrète contenant au moins `niveau` de la probabilité."""
    c = np.cumsum(loi)
    a = int(np.searchsorted(c, (1 - niveau) / 2))
    b = int(np.searchsorted(c, 1 - (1 - niveau) / 2))
    return a, min(b, len(loi) - 1)


def attendus(r: dict) -> dict:
    """Statistiques attendues (moyenne + intervalle à 80 %) : buts, corners, cartons jaunes."""
    M = r["_M"]; G = np.arange(M.shape[0])
    tot = np.bincount((G[:, None] + G[None, :]).ravel(), weights=M.ravel())
    out = {"goals": {"mean": _r(r["buts_dom"] + r["buts_ext"], 2), "range": intervalle(tot), "home": _r(r["buts_dom"], 2), "away": _r(r["buts_ext"], 2),
                     "dist": [_r(q, 3) for q in tot[:7]]}}
    for cle, nom in (("corners", "corners"), ("jaunes", "cards")):
        if cle in r:
            loi = r[cle]["loi"]
            out[nom] = {"mean": _r(r[cle]["total"], 1), "range": intervalle(loi), "home": _r(r[cle]["dom"], 1), "away": _r(r[cle]["ext"], 1)}
    return out


# ---------------------------------------------------------------- matchs comparables
class Comparables:
    """Matchs historiques les plus proches (écart d'Elo, niveau offensif, ligue) : ce qui s'est réellement passé dans des
    situations semblables. Statistique descriptive, indépendante du modèle de régression."""

    def __init__(self, X: pd.DataFrame, saisons: int = 10, k: int = 400):
        H = X[X.Season >= X.Season.max() - saisons].dropna(subset=["dElo", "Otot", "HomeCorners", "HomeYellow"])
        self.H, self.k = H, k
        self.Z = np.c_[H.dElo.values / 1.0, H.Otot.values / 1.5]

    def chercher(self, v: dict, division: str | None = None) -> dict | None:
        if not len(self.H):
            return None
        z = np.array([v["dElo"], v["Otot"] / 1.5])
        dist = np.sqrt(((self.Z - z) ** 2).sum(1)) + np.where(self.H.Division.values == division, 0, 0.15)
        idx = np.argsort(dist)[: self.k]
        S = self.H.iloc[idx]
        g = S.FTHome + S.FTAway
        return {"n": int(len(S)), "homeWin": _r((S.FTHome > S.FTAway).mean()), "draw": _r((S.FTHome == S.FTAway).mean()),
                "awayWin": _r((S.FTHome < S.FTAway).mean()), "avgGoals": _r(g.mean(), 2), "over25": _r((g > 2.5).mean()),
                "btts": _r(((S.FTHome > 0) & (S.FTAway > 0)).mean()), "corners": _r((S.HomeCorners + S.AwayCorners).mean(), 1),
                "cards": _r((S.HomeYellow + S.AwayYellow).mean(), 1),
                "eloGap": [int(round(100 * S.dElo.min())), int(round(100 * S.dElo.max()))]}


# ---------------------------------------------------------------- cotes
def marche(r: dict, cotes: dict | None) -> dict | None:
    """Probabilités implicites des cotes (marge retirée, méthode de Shin) et écarts avec le modèle."""
    if not cotes or not all(cotes.get(k) for k in ("home", "draw", "away")):
        return None
    pm, marge = shin([cotes["home"], cotes["draw"], cotes["away"]])
    lignes = [("1", "home", r["1"], pm[0]), ("X", "draw", r["X"], pm[1]), ("2", "away", r["2"], pm[2])]
    out = {"odds": {k: _r(v, 2) for k, v in cotes.items()}, "margin": _r(marge, 4),
           "home": _r(pm[0], 4), "draw": _r(pm[1], 4), "away": _r(pm[2], 4), "rows": []}
    if cotes.get("over25") and cotes.get("under25"):
        po, mo = shin([cotes["over25"], cotes["under25"]])
        out["over25"] = _r(po[0], 4)
        lignes.append(("+2,5", "over25", r["over25"], po[0]))
    for lab, k, pmod, pmar in lignes:
        out["rows"].append({"key": k, "label": lab, "model": _r(pmod, 4), "market": _r(pmar, 4), "gap": _r(pmod - pmar, 4),
                            "fairOdds": _r(1 / pmod, 2), "odds": _r(cotes.get(k), 2)})
    ecart = max(abs(x["gap"]) for x in out["rows"][:3])
    out["agreement"] = "accord" if ecart < 0.05 else ("désaccord modéré" if ecart < 0.10 else "désaccord marqué")
    out["note"] = ("Le modèle et le marché concordent." if ecart < 0.05 else
                   "Le marché intègre des informations absentes du modèle (compositions, blessures, actualité). "
                   "Historiquement, quand ils divergent, c'est le marché qui est le plus souvent juste.")
    return out


# ---------------------------------------------------------------- contexte
def contexte(k: dict | None, dom: str, ext: str) -> dict | None:
    if not k:
        return None
    pick = lambda s: {"rest": k.get(f"repos_{s}"), "load21": k.get(f"charge_{s}"), "played": k.get(f"joues_{s}"), "rank": k.get(f"rang_{s}"),
                      "promoted": bool(k.get(f"promu_{s}")), "firstSeason": bool(k.get(f"premiere_{s}")), "champion": bool(k.get(f"champion_{s}")),
                      "titleRace": bool(k.get(f"titre_{s}")), "europeRace": bool(k.get(f"europe_{s}")), "relegationFight": bool(k.get(f"maintien_{s}")),
                      "nothingToPlayFor": bool(k.get(f"sansenjeu_{s}"))}
    return {"home": pick("h"), "away": pick("a"), "notes": K.description(k, dom, True) + K.description(k, ext, False),
            "seasonStart": bool(min(k.get("joues_h") or 0, k.get("joues_a") or 0) < K.DEBUT_SAISON)}
