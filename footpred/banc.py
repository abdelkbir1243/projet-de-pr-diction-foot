"""Banc d'essai scientifique : prédictions hors échantillon (out-of-fold) strictement chronologiques.

Pour chaque saison s, tous les modèles sont entraînés sur les saisons < s uniquement et prédisent la saison s. Le résultat
(un tableau par match + matrices de scores) sert ensuite, sans jamais réentraîner sur l'avenir :
  - à apprendre l'ensemble et la calibration (fenêtre A) ;
  - à apprendre le moteur de sélection, ses seuils et son méta-modèle (fenêtre B) ;
  - à l'évaluation finale sur une saison réservée (fenêtre T), jamais utilisée pour un choix.

Découpage (footpred.config) : A = 2016-2020, B = 2021-2024, T = 2025 (2025/26). La saison en cours (2026/27) constitue
l'évaluation prospective (journal des prédictions figées avant le coup d'envoi).
"""
import time

import numpy as np
import pandas as pd

from . import config as C
from .markets import shin
from .models import Modele1X2, ModeleButs, poids

FENETRE_A = list(range(2016, 2021))
FENETRE_B = list(range(2021, 2025))
FENETRE_T = [2025]

FE_ELO = ["dElo", "absElo"]
FE_E1 = ["dElo", "absElo", "dQ", "Otot"]                      # Elo + forme (xG proxy)
ABLATIONS = {                                                  # familles retirées du modèle v5 (logit 1X2)
    "sans Elo": ["dElo", "absElo"],
    "sans forme / xG proxy": ["dQ", "Otot"],
    "sans pi-ratings": ["pi_diff", "pi_diff_avg"],
    "sans ratings de buts GAS": ["g_lh", "g_la"],
    "sans contexte (enjeu)": list(C.MOTIVATION),
    "sans effets ligue": ["lg_SP1", "lg_I1", "lg_D1", "lg_F1"],
}
COLS_META = ["Season", "MatchDate", "Division", "HomeTeam", "AwayTeam", "FTHome", "FTAway", "y", "OddHome", "OddDraw", "OddAway",
             "Over25", "Under25", "joues_h", "joues_a"]


def proba_marche(df: pd.DataFrame) -> np.ndarray:
    """Probabilités 1X2 sans marge (méthode de Shin) ; NaN si cotes absentes."""
    out = np.full((len(df), 3), np.nan)
    o = df[["OddHome", "OddDraw", "OddAway"]].values.astype(float)
    for i in np.where(np.isfinite(o).all(1) & (o > 1).all(1))[0]:
        out[i] = shin(o[i])[0]
    return out


def proba_over25_marche(df: pd.DataFrame) -> np.ndarray:
    ov, un = df.get("Over25"), df.get("Under25")
    if ov is None or un is None:
        return np.full(len(df), np.nan)
    a, b = 1 / ov.values.astype(float), 1 / un.values.astype(float)
    return a / (a + b)


def _catboost(TR: pd.DataFrame, s_ref: int, cols, seed=0):
    from catboost import CatBoostClassifier
    m = CatBoostClassifier(iterations=500, depth=4, learning_rate=0.05, l2_leaf_reg=5, loss_function="MultiClass",
                           random_seed=seed, verbose=False, thread_count=-1, allow_writing_files=False)
    return m.fit(TR[cols], TR.y, sample_weight=poids(TR, s_ref))


def generer(X: pd.DataFrame, saisons=None, catboost=True, ablations=True, journal=print) -> dict:
    """Prédictions hors échantillon pour chaque saison. Renvoie {"meta": DataFrame, "P": {modèle: (n, 3)}, "M": (n, 11, 11),
    "lambdas": (n, 2), "rho": {saison: ρ}}. Aucune information de la saison prédite n'entre dans l'entraînement."""
    saisons = saisons or FENETRE_A + FENETRE_B + FENETRE_T
    metas, P, Ms, L, rho = [], {}, [], [], {}
    for s in saisons:
        t0 = time.time()
        TR, TE = X[X.Season < s], X[X.Season == s]
        if len(TE) == 0:
            continue
        assert TR.MatchDate.max() < TE.MatchDate.min(), "fuite temporelle : entraînement postérieur au test"
        out = {"E0 Goalgebra v5 (logit)": Modele1X2(C.FE).fit(TR, s - 1).predict(TE),
               "Elo seul": Modele1X2(FE_ELO).fit(TR, s - 1).predict(TE),
               "E1 Logistique Elo + forme": Modele1X2(FE_E1).fit(TR, s - 1).predict(TE)}
        mb = ModeleButs(C.FE_B).fit(TR, s - 1)
        M = mb.grilles(TE); rho[s] = float(mb.rho)
        out["E2 Dixon-Coles (buts)"] = np.stack([np.tril(M, -1).sum((1, 2)), np.trace(M, axis1=1, axis2=2), np.triu(M, 1).sum((1, 2))], 1)
        if catboost:
            out["E3 CatBoost (sport)"] = _catboost(TR, s - 1, C.FE).predict_proba(TE[C.FE])
        if ablations and s in FENETRE_B + FENETRE_T:
            for nom, retire in ABLATIONS.items():
                cols = [c for c in C.FE if c not in retire]
                out[f"ablation · {nom}"] = Modele1X2(cols).fit(TR, s - 1).predict(TE)
        out["E5 Marché seul (Shin)"] = proba_marche(TE)
        for k, v in out.items():
            P.setdefault(k, []).append(v)
        Ms.append(M); L.append(np.stack(mb.lambdas(TE), 1))
        metas.append(TE[[c for c in COLS_META if c in TE.columns]].assign(over25_marche=proba_over25_marche(TE)))
        journal(f"saison {s}/{(s + 1) % 100:02d} : {len(TE)} matchs, {time.time() - t0:.0f} s")
    return {"meta": pd.concat(metas, ignore_index=True), "P": {k: np.concatenate(v) for k, v in P.items()},
            "M": np.concatenate(Ms).astype(np.float32), "lambdas": np.concatenate(L), "rho": rho}
