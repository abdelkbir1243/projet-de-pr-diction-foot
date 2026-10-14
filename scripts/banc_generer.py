"""Génère les prédictions hors échantillon du banc d'essai (≈ 15-25 min) → data/banc_oof.pkl (non versionné)."""
import os, pickle, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from footpred.banc import generer          # noqa: E402
from footpred.data import charger_matchs   # noqa: E402
from footpred.features import construire   # noqa: E402

t0 = time.time()
d = construire(charger_matchs(cache="data/Matches.csv"))
print("colonnes contexte présentes :", [c for c in ("joues_h", "joues_a") if c in d.X.columns], "| saisons", d.X.Season.min(), "→", d.X.Season.max(), flush=True)
B = generer(d.X, journal=lambda m: print(m, flush=True))
pickle.dump(B, open("data/banc_oof.pkl", "wb"))
print(f"terminé en {time.time() - t0:.0f} s : {len(B['meta'])} matchs, modèles : {list(B['P'])}")
