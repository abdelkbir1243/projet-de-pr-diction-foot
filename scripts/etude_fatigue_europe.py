"""Fatigue : un match européen en semaine pèse-t-il sur le match de championnat suivant ? (docs/resultats.md §15)

Résidu = points obtenus − points attendus par le modèle (prédictions hors échantillon, chaque saison prédite par un modèle
entraîné sur les précédentes). Un résidu négatif signifie que l'équipe fait moins bien que prévu.
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from footpred import coupes as K                           # noqa: E402
from footpred import evaluation as E                       # noqa: E402
from footpred.data import charger_matchs                    # noqa: E402
from footpred.features import construire                    # noqa: E402


def main():
    raw = charger_matchs()
    textes = {}
    for f in glob.glob(os.path.join("data", "coupes", "*.txt")):
        c, s = os.path.basename(f)[:-4].split("_"); textes[(c, s)] = open(f, encoding="utf-8").read()
    if not textes:
        textes = K.telecharger("data/coupes")
    V, _ = K.variables(K.charger(textes), raw)
    euro = pd.concat([V[["date", "home_ds"]].rename(columns={"home_ds": "t"}), V[["date", "away_ds"]].rename(columns={"away_ds": "t"})])
    euro = euro[euro.t.apply(lambda x: isinstance(x, str))]
    dates = {t: np.sort(g.date.values) for t, g in euro.groupby("t")}

    d = construire(raw)
    te, r = E.walk_forward(d.X, list(range(2012, 2026)))
    P = r["P"]
    te = te.assign(xh=3 * P[:, 0] + P[:, 1], xa=3 * P[:, 2] + P[:, 1],
                   ph=np.select([te.y == 0, te.y == 1], [3, 1], 0), pa=np.select([te.y == 2, te.y == 1], [3, 1], 0))

    def jours_depuis(t, jour):
        s = dates.get(t)
        if s is None:
            return np.nan
        i = np.searchsorted(s, np.datetime64(jour), side="left")
        return np.nan if i == 0 else (np.datetime64(jour) - s[i - 1]) / np.timedelta64(1, "D")

    te["eh"] = [jours_depuis(t, j) for t, j in zip(te.HomeTeam, te.MatchDate)]
    te["ea"] = [jours_depuis(t, j) for t, j in zip(te.AwayTeam, te.MatchDate)]
    rows = []
    for nom, mh, ma in [("match européen 2-3 jours avant", te.eh.between(1, 3), te.ea.between(1, 3)),
                        ("match européen 4-5 jours avant", te.eh.between(4, 5), te.ea.between(4, 5)),
                        ("équipe européenne, pas de match dans les 7 jours", te.eh > 7, te.ea > 7)]:
        res = np.r_[(te.ph - te.xh)[mh].values, (te.pa - te.xa)[ma].values]
        ic = E.ic_bootstrap(res)
        rows.append({"situation": nom, "matchs": len(res), "écart (pts/match)": res.mean(), "ic_bas": ic[0], "ic_haut": ic[1]})
    t = pd.DataFrame(rows).set_index("situation")
    print(t.round(3))
    os.makedirs("results/tables", exist_ok=True)
    t.round(4).to_csv("results/tables/fatigue_europe.csv")


if __name__ == "__main__":
    main()
