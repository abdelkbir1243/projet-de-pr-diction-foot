"""Reproduit tous les résultats du rapport dans results/ (tables CSV + figures PNG).  Usage : python scripts/reproduire.py [--saison 2025]"""
import argparse, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import matplotlib; matplotlib.use("Agg")
from footpred import preparer, labo

ap = argparse.ArgumentParser(); ap.add_argument("--saison", type=int, default=2025); ap.add_argument("--source", default=None)
a = ap.parse_args()
t = time.time(); pred = preparer(a.source); d = pred.d
print(f"Données au {d.date_max.date()} — {len(d.X)} matchs avec variables ({time.time() - t:.0f} s)")
for nom, f in [("validation_2021_2026", lambda: labo.validation(d)), (f"saison_{a.saison}", lambda: labo.saison(d, a.saison)),
               (f"hebdo_{a.saison}", lambda: labo.hebdo(d, a.saison)), ("strategies_2021_2026", lambda: labo.strategies(d)), ("corners_cartons_2021_2026", lambda: labo.stats_match(d)),
               ("decisions_2021_2026", lambda: labo.fiabilite_decisions(d))]:
    t = time.time(); r = f(); labo.enregistrer(r, nom); print(f"\n=== {nom} ({time.time() - t:.0f} s)"); labo.afficher(r)
pred.formules().to_csv("results/tables/formules_modele_final.csv")
print("\nTerminé : voir results/tables et results/figures")
