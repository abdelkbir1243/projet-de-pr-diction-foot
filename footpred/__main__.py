"""Ligne de commande :
    python -m footpred predire "Arsenal" "Chelsea" [--cotes 1.8 3.9 4.5]
    python -m footpred journee "Arsenal vs Chelsea" "Inter vs Milan@2026-10-04"      # ajoute au journal
    python -m footpred evaluer                                        # note le journal
    python -m footpred valider                                        # walk-forward 2021-2026
    python -m footpred saison 2025                                    # test d'une saison figée
"""
import argparse
import numpy as np
from . import preparer, config as C, evaluation as E, journal as J
from .data import charger_matchs
from .features import construire


def main():
    ap = argparse.ArgumentParser(prog="footpred", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=None, help="chemin ou URL de Matches.csv")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("predire"); p.add_argument("dom"); p.add_argument("ext"); p.add_argument("--cotes", nargs=3, type=float)
    p = sp.add_parser("journee"); p.add_argument("matchs", nargs="+", help='"Dom vs Ext" ou "Dom vs Ext@AAAA-MM-JJ"')
    sp.add_parser("evaluer"); sp.add_parser("valider")
    p = sp.add_parser("saison"); p.add_argument("saison", type=int)
    a = ap.parse_args()

    if a.cmd == "evaluer":
        J.evaluer_journal(source=a.source); return
    if a.cmd in ("valider", "saison"):
        d = construire(charger_matchs(a.source))
        te, r = E.walk_forward(d.X, [a.saison] if a.cmd == "saison" else C.SAISONS_TEST)
        y = te.y.values; Pm = E.proba_cotes(te); ok = ~np.isnan(Pm).any(1)
        print(f"{len(te)} matchs — modèle v5 :", {k: round(v, 4) for k, v in E.resume(r["P"], y).items()})
        print(f"{ok.sum()} matchs — cotes      :", {k: round(v, 4) for k, v in E.resume(Pm[ok], y[ok]).items()})
        return
    pred = preparer(a.source)
    if a.cmd == "predire":
        pred.simulation(a.dom, a.ext, cotes=a.cotes)
    elif a.cmd == "journee":
        ms = []
        for s in a.matchs:
            s, _, date = s.partition("@"); dom, _, ext = s.partition(" vs "); ms.append((dom.strip(), ext.strip(), date))
        J.predire_journee(pred, ms)


if __name__ == "__main__":
    main()
