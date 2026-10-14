"""Comparaison de tous les modèles sur EXACTEMENT les mêmes matchs (évaluation rétrospective walk-forward 2021/22 → 2025/26).

Répond à une critique légitime : dans les versions précédentes du README, v3/v4/Elo étaient évalués sur 8 821 matchs et v5 sur
8 897 (v5 prédit aussi les promus grâce à leurs matchs de deuxième division). Ici, tous les modèles utilisent les mêmes
variables d'entrée (construites avec la deuxième division) et sont notés sur le même ensemble de matchs, celui où les cotes
existent, pour que la ligne « Cotes » soit comparable.

    python scripts/comparaison_commune.py            → results/tables/comparaison_commune_*.csv
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from footpred import config as C                                         # noqa: E402
from footpred import evaluation as E                                     # noqa: E402
from footpred.data import charger_matchs                                 # noqa: E402
from footpred.features import construire                                 # noqa: E402

SAISONS = [2021, 2022, 2023, 2024, 2025]
FE_ELO = ["dElo", "absElo"]
SORTIE = os.path.join(os.path.dirname(__file__), "..", "results", "tables")


def main():
    raw = charger_matchs(cache="data/Matches.csv")
    d = construire(raw)
    X = d.X
    te, v5 = E.walk_forward(X, SAISONS, C.FE, C.FE_B)
    _, v4 = E.walk_forward(X, SAISONS, C.FE_V4, C.FE_B_V4)
    _, v3 = E.walk_forward(X, SAISONS, C.FE_V3, C.FE_B_V3)
    _, elo = E.walk_forward(X, SAISONS, FE_ELO, FE_ELO)
    y = te.y.values
    freq = np.zeros((len(te), 3))
    for s in SAISONS:
        TR = X[X.Season < s]; w = 0.5 ** ((s - 1 - TR.Season) / C.DEMI_VIE)
        f = np.bincount(TR.y, weights=w, minlength=3); freq[(te.Season == s).values] = f / f.sum()
    R = {"Fréquences": freq, "Elo seul": elo["P"], "v3": v3["P"], "v4": v4["P"], "v5": v5["P"], "Cotes": E.proba_cotes(te)}
    ok = np.all([~np.isnan(P).any(1) for P in R.values()], axis=0)             # matchs communs à tous les modèles
    T = pd.DataFrame({k: E.resume(P[ok], y[ok]) for k, P in R.items()}).T
    T.insert(0, "matchs", int(ok.sum()))
    T["skill vs fréquences"] = 1 - T["log loss"] / T.loc["Fréquences", "log loss"]
    ll = {k: E.log_loss(P[ok], y[ok]) for k, P in R.items()}
    tests = []
    for a, b in (("v5", "v4"), ("v4", "v3"), ("v5", "Elo seul"), ("v5", "Cotes")):
        dd = ll[a] - ll[b]; lo, hi = E.ic_bootstrap(dd)
        tests.append({"comparaison": f"{a} − {b}", "Δ log loss ×1e3": 1000 * dd.mean(), "IC bas": 1000 * lo, "IC haut": 1000 * hi,
                      "significatif": bool(hi < 0 or lo > 0)})
    tests = pd.DataFrame(tests).set_index("comparaison")
    os.makedirs(SORTIE, exist_ok=True)
    T.round(4).to_csv(os.path.join(SORTIE, "comparaison_commune_1X2.csv"))
    tests.round(2).to_csv(os.path.join(SORTIE, "comparaison_commune_tests.csv"))
    print(T.round(4).to_string()); print(); print(tests.round(2).to_string())


if __name__ == "__main__":
    main()
