"""Confronte deux articles à nos données (docs/resultats.md §14).

- Ren & Susnjak (2022), arXiv:2211.15734 : la dispersion des cotes (« Kelly Index ») sépare-t-elle des matchs plus prévisibles,
  au-delà de la netteté du favori ?
- Sallis, Georgoulas & Tsoulos (2026), Computation 14(9):195 : méthode de la puissance pour retirer la marge, comparée à Shin
  et à la normalisation proportionnelle.

    python scripts/etude_articles_2026.py
"""
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import brentq

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from footpred import evaluation as E                     # noqa: E402
from footpred.data import charger_matchs                  # noqa: E402
from footpred.features import construire                  # noqa: E402
from footpred.markets import shin                         # noqa: E402


def puissance(inv):
    k = brentq(lambda k: (inv ** k).sum() - 1, 0.5, 2.0)
    return inv ** k


def main():
    d = construire(charger_matchs())
    te, r = E.walk_forward(d.X, list(range(2012, 2026)))
    P = r["P"]; y_all = te.y.values
    O = te[["OddHome", "OddDraw", "OddAway"]].values.astype(float)
    Mx = te[["MaxHome", "MaxDraw", "MaxAway"]].values.astype(float)
    ok = np.isfinite(O).all(1) & (O > 1).all(1) & np.isfinite(Mx).all(1)
    O, Mx, y, Pmod = O[ok], Mx[ok], y_all[ok], P[ok]
    inv = 1 / O
    methodes = {"proportionnelle": inv / inv.sum(1, keepdims=True), "puissance": np.array([puissance(i) for i in inv]),
                "Shin": np.array([shin(o)[0] for o in O])}
    methodes["Shin"] /= methodes["Shin"].sum(1, keepdims=True)
    tab = pd.DataFrame({k: {"log_loss": E.log_loss(v, y).mean(), "brier": E.brier(v, y).mean(), "rps": E.rps(v, y).mean(), "ece": E.ece(v, y)}
                        for k, v in methodes.items()}).T
    print(f"{len(y)} matchs\n", tab.round(5))
    for a in ("puissance", "proportionnelle"):
        dd = E.log_loss(methodes[a], y) - E.log_loss(methodes["Shin"], y)
        print(f"{a} − Shin : {1e3 * dd.mean():+.2f} ×10⁻³, IC {np.round(1e3 * E.ic_bootstrap(dd), 2)}")

    sh = methodes["Shin"]
    t = pd.DataFrame({"disp": (Mx / O - 1).max(1), "pm": sh.max(1), "pm_ok": sh.argmax(1) == y, "pmod": Pmod.max(1), "mod_ok": Pmod.argmax(1) == y,
                      "dll": E.log_loss(Pmod, y) - E.log_loss(sh, y)})
    t["groupe"] = pd.qcut(t.disp, 3, labels=["faible", "moyenne", "forte"])
    print(t.groupby("groupe", observed=True).agg(n=("pm", "size"), annonce=("pm", "mean"), realise=("pm_ok", "mean"),
                                                  modele_moins_marche=("dll", "mean")).round(4))
    t["lp"] = np.log(t.pm / (1 - t.pm))
    print(sm.Logit(t.pm_ok.astype(float), sm.add_constant(t[["lp", "disp"]])).fit(disp=0).summary2().tables[1][["Coef.", "P>|z|"]])


if __name__ == "__main__":
    main()
