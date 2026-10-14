"""Métriques probabilistes et protocoles de validation (walk-forward par saison, saison figée, saison semaine par semaine)."""
import numpy as np
import pandas as pd
from . import config as C
from .models import Modele1X2, ModeleButs

# ---------------------------------------------------------------- métriques
def log_loss(P, y):
    return -np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1))


def log_loss_binaire(p, o):
    return -np.log(np.clip(np.where(o, p, 1 - p), 1e-12, 1))


def rps(P, y):
    """Ranked Probability Score (tient compte de l'ordre 1 < X < 2)."""
    c = np.cumsum(P - np.eye(3)[y], 1)[:, :2]
    return (c ** 2).sum(1) / 2


def brier(P, y):
    return ((P - np.eye(3)[y]) ** 2).sum(1)


def ece(P, y, bins=10):
    """Expected Calibration Error moyenne sur les 3 issues (déciles de probabilité)."""
    e = 0
    for k in range(3):
        b = pd.qcut(P[:, k], bins, labels=False, duplicates="drop")
        g = pd.DataFrame({"p": P[:, k], "o": y == k, "b": b}).groupby("b")
        e += (g.p.mean() - g.o.mean()).abs().mul(g.size() / len(y)).sum()
    return e / 3


def ic_bootstrap(d, k=2000, seed=0):
    """IC 95 % de la moyenne de d (bootstrap apparié : d = différence match par match entre deux modèles)."""
    d = np.asarray(d); b = d[np.random.default_rng(seed).integers(0, len(d), (k, len(d)))].mean(1)
    return np.percentile(b, [2.5, 97.5])


def proba_cotes(df):
    """Probabilités implicites des cotes (normalisation proportionnelle) ; NaN si cotes absentes."""
    inv = 1 / df[["OddHome", "OddDraw", "OddAway"]].values
    return inv / inv.sum(1, keepdims=True)


def resume(P, y):
    return {"log loss": log_loss(P, y).mean(), "RPS": rps(P, y).mean(), "Brier": brier(P, y).mean(),
            "ECE": ece(P, y), "bon résultat": np.mean(P.argmax(1) == y)}


# ---------------------------------------------------------------- prédiction d'un bloc de matchs
def predire_bloc(TR, TE, s_ref, fe=None, fe_b=None):
    """Entraîne sur TR, prédit TE : probabilités 1X2, λ, P(over 2,5), P(BTTS), P(score exact observé)."""
    P = Modele1X2(fe).fit(TR, s_ref).predict(TE)
    mb = ModeleButs(fe_b).fit(TR, s_ref); Ms = mb.grilles(TE); lh, la = mb.lambdas(TE)
    G = np.arange(Ms.shape[1]); tot = G[:, None] + G[None, :]
    x, y = TE.FTHome.clip(upper=C.GMAX).astype(int).values, TE.FTAway.clip(upper=C.GMAX).astype(int).values
    return {"P": P, "lh": lh, "la": la, "over25": (Ms * (tot > 2.5)).sum((1, 2)), "btts": Ms[:, 1:, 1:].sum((1, 2)),
            "p_score": Ms[np.arange(len(TE)), x, y]}


def _concat(parts, n):
    out = {k: np.zeros((n, 3)) if k == "P" else np.zeros(n) for k in parts[0][1]}
    for m, r in parts:
        for k, v in r.items():
            out[k][m] = v
    return out


def walk_forward(X, saisons=C.SAISONS_TEST, fe=None, fe_b=None):
    """Chaque saison est prédite par un modèle entraîné sur les saisons précédentes uniquement."""
    te = X[X.Season.isin(saisons)]
    parts = []
    for s in saisons:
        m = (te.Season == s).values
        parts.append((m, predire_bloc(X[X.Season < s], te[m], s - 1, fe, fe_b)))
    return te, _concat(parts, len(te))


def saison_hebdo(X, saison, ligues=None, fe=None, fe_b=None):
    """Rejoue une saison semaine par semaine : chaque lundi, ré-entraînement sur tout ce qui précède."""
    te = X[(X.Season == saison) & X.Division.isin(ligues or list(C.LIGUES))].sort_values("MatchDate")
    semaine = te.MatchDate.dt.to_period("W-SUN").dt.start_time
    parts = []
    for lundi in semaine.unique():
        m = (semaine == lundi).values
        parts.append((m, predire_bloc(X[X.MatchDate < lundi], te[m], saison, fe, fe_b)))
    return te.assign(semaine=semaine.values), _concat(parts, len(te))
