"""Marchés dérivés de la grille des scores, cotes justes et retrait de la marge (méthode de Shin)."""
import numpy as np
from scipy.optimize import minimize_scalar


def marches(M: np.ndarray, k_ht: float, lh: float, la: float) -> dict:
    G = np.arange(M.shape[0]); tot = G[:, None] + G[None, :]
    return {
        "1 (grille)": np.tril(M, -1).sum(), "X (grille)": np.trace(M), "2 (grille)": np.triu(M, 1).sum(),
        "over15": M[tot > 1.5].sum(), "over25": M[tot > 2.5].sum(), "over35": M[tot > 3.5].sum(),
        "btts": M[1:, 1:].sum(), "cs_dom": M[:, 0].sum(), "cs_ext": M[0, :].sum(),
        "but_1re_MT": 1 - np.exp(-k_ht * (lh + la)),
    }


def scores_probables(M: np.ndarray, k: int = 5, gmax: int = 6):
    return sorted(((M[i, j], f"{i}-{j}") for i in range(gmax) for j in range(gmax)), reverse=True)[:k]


def cote_juste(p: float) -> float:
    return 1 / p if p > 0 else np.inf


def shin(cotes) -> tuple[np.ndarray, float]:
    """Probabilités implicites sans marge (Shin 1993) ; renvoie (probabilités, marge du bookmaker)."""
    pi = 1 / np.asarray(cotes, float); S = pi.sum()
    f = lambda z: (np.sqrt(z * z + 4 * (1 - z) * pi * pi / S) - z).sum() / (2 * (1 - z)) - 1
    z = minimize_scalar(lambda z: f(z) ** 2, bounds=(0, .4), method="bounded").x
    return (np.sqrt(z * z + 4 * (1 - z) * pi * pi / S) - z) / (2 * (1 - z)), S - 1
