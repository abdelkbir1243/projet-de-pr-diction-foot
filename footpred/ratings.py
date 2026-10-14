"""Ratings dynamiques calculés match après match, dans l'ordre chronologique, sur TOUTES les ligues du dataset.

Chaque fonction renvoie les valeurs AVANT chaque match (aucune fuite) et conserve l'état final pour prédire les matchs à venir.
"""
import numpy as np
import pandas as pd
from .config import PI, GAS


class PiRatings:
    """pi-ratings (Constantinou & Fenton 2013) : une note domicile et une note extérieur par équipe."""

    def __init__(self, lr=PI["lr"], gamma=PI["gamma"], b=PI["b"], c=PI["c"]):
        self.lr, self.gamma, self.b, self.c = lr, gamma, b, c
        self.notes: dict[str, list[float]] = {}

    def _attendu(self, r):
        return np.sign(r) * (self.b ** (abs(r) / self.c) - 1)

    def calculer(self, d: pd.DataFrame) -> np.ndarray:
        out = np.zeros((len(d), 4))
        for i, (h, a, gh, ga) in enumerate(zip(d.HomeTeam.values, d.AwayTeam.values, d.FTHome.values, d.FTAway.values)):
            rh = self.notes.setdefault(h, [0.0, 0.0]); ra = self.notes.setdefault(a, [0.0, 0.0])
            out[i] = rh[0], rh[1], ra[0], ra[1]
            if np.isnan(gh):
                continue
            e = (gh - ga) - (self._attendu(rh[0]) - self._attendu(ra[1]))
            s = np.sign(e) * self.c * np.log10(1 + abs(e))
            o0, o1 = rh[0], ra[1]
            rh[0] += s * self.lr; rh[1] += (rh[0] - o0) * self.gamma
            ra[1] -= s * self.lr; ra[0] += (ra[1] - o1) * self.gamma
        return out

    def note(self, equipe):
        return self.notes.get(equipe, [0.0, 0.0])


class GasRatings:
    """Ratings de buts à score (GAS, Koopman & Lit 2019).

    log λ_dom = μ_L + h_L + att_dom − déf_ext ;  log λ_ext = μ_L − h_L + att_ext − déf_dom
    Après le match : att_dom += η (buts_dom − λ_dom), déf_ext −= η (buts_dom − λ_dom), et symétriquement.
    Changement de division (promu / relégué) : att et déf multipliés par `shrink`.
    """

    def __init__(self, eta=GAS["eta"], eta_l=GAS["eta_l"], shrink=GAS["shrink"], mu0=GAS["mu0"], ha0=GAS["ha0"]):
        self.eta, self.eta_l, self.shrink, self.mu0, self.ha0 = eta, eta_l, shrink, mu0, ha0
        self.att, self.dfn, self.mu, self.ha, self.last = {}, {}, {}, {}, {}

    def calculer(self, d: pd.DataFrame) -> np.ndarray:
        att, dfn, mu, ha, last, eta = self.att, self.dfn, self.mu, self.ha, self.last, self.eta
        out = np.full((len(d), 2), np.nan)
        for i, (h, a, L, gh, ga) in enumerate(zip(d.HomeTeam.values, d.AwayTeam.values, d.Division.values, d.FTHome.values, d.FTAway.values)):
            m = mu.setdefault(L, self.mu0); hh = ha.setdefault(L, self.ha0)
            for t in (h, a):
                if t in last and last[t] != L:
                    att[t] *= self.shrink; dfn[t] *= self.shrink
                last[t] = L
            ah, dh, aa, da = att.get(h, 0.), dfn.get(h, 0.), att.get(a, 0.), dfn.get(a, 0.)
            lh, la = m + hh + ah - da, m - hh + aa - dh
            out[i] = lh, la
            if np.isnan(gh) or np.isnan(ga):
                continue
            eh, ea = gh - np.exp(lh), ga - np.exp(la)
            att[h], dfn[a], att[a], dfn[h] = ah + eta * eh, da - eta * eh, aa + eta * ea, dh - eta * ea
            mu[L], ha[L] = m + self.eta_l * (eh + ea), hh + self.eta_l * (eh - ea)
        return out

    def log_lambdas(self, dom, ext, ligue):
        """log λ attendus pour un match à venir dans `ligue` (rétrécissement si l'équipe change de division)."""
        def f(t, k):
            v = getattr(self, k).get(t, 0.)
            return v * (self.shrink if self.last.get(t, ligue) != ligue else 1.0)
        m, hh = self.mu.get(ligue, self.mu0), self.ha.get(ligue, self.ha0)
        return m + hh + f(dom, "att") - f(ext, "dfn"), m - hh + f(ext, "att") - f(dom, "dfn")
