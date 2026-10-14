"""Modèles statistiques : logit multinomial (1X2) et Poisson + Dixon-Coles (buts)."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import minimize_scalar
from scipy.stats import poisson, nbinom
from sklearn.linear_model import LogisticRegression
from . import config as C


def poids(df: pd.DataFrame, s_ref: int) -> pd.Series:
    """Pondération temporelle : 0,5^((s_ref − saison)/demi-vie)."""
    return 0.5 ** ((s_ref - df.Season) / C.DEMI_VIE)


def tau(x, y, lh, la, r):
    """Correction de Dixon & Coles (1997) pour les scores 0-0, 1-0, 0-1, 1-1."""
    t = np.ones(np.broadcast(x, y, lh).shape)
    t = np.where((x == 0) & (y == 0), 1 - lh * la * r, t)
    t = np.where((x == 0) & (y == 1), 1 + lh * r, t)
    t = np.where((x == 1) & (y == 0), 1 + la * r, t)
    t = np.where((x == 1) & (y == 1), 1 - r, t)
    return t


def grille(lh: float, la: float, rho: float, gmax: int = C.GMAX) -> np.ndarray:
    """Matrice M[i, j] = P(score i-j)."""
    G = np.arange(gmax + 1)
    M = poisson.pmf(G[:, None], lh) * poisson.pmf(G[None, :], la) * tau(G[:, None], G[None, :], lh, la, rho)
    return M / M.sum()


class Modele1X2:
    """P(1), P(X), P(2) par régression logistique multinomiale pondérée dans le temps."""

    def __init__(self, cols=None):
        self.cols = list(cols or C.FE)

    def fit(self, TR: pd.DataFrame, s_ref: int):
        self.lr = LogisticRegression(C=1e6, max_iter=30000, tol=1e-8).fit(TR[self.cols], TR.y, sample_weight=poids(TR, s_ref))
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return self.lr.predict_proba(df[self.cols])

    def coefficients(self) -> pd.DataFrame:
        """Coefficients lisibles, nul = référence : z1 = log[P(1)/P(X)], z2 = log[P(2)/P(X)]."""
        i, c = self.lr.intercept_, self.lr.coef_
        return pd.DataFrame({"log[P(1)/P(X)]": np.r_[i[0] - i[1], c[0] - c[1]], "log[P(2)/P(X)]": np.r_[i[2] - i[1], c[2] - c[1]]},
                            index=["constante"] + self.cols)


class ModeleButs:
    """Buts domicile et extérieur : deux régressions de Poisson + paramètre ρ de Dixon-Coles (maximum de vraisemblance)."""

    def __init__(self, cols=None):
        self.cols = list(cols or C.FE_B)

    def fit(self, TR: pd.DataFrame, s_ref: int):
        w, Xa = poids(TR, s_ref), sm.add_constant(TR[self.cols])
        self.gh = sm.GLM(TR.FTHome, Xa, family=sm.families.Poisson(), freq_weights=w).fit()
        self.ga = sm.GLM(TR.FTAway, Xa, family=sm.families.Poisson(), freq_weights=w).fit()
        lh, la = self.gh.predict(Xa).values, self.ga.predict(Xa).values
        nll = lambda r: -np.sum(w * np.log(np.clip(tau(TR.FTHome.values, TR.FTAway.values, lh, la, r), 1e-12, None)))
        self.rho = minimize_scalar(nll, bounds=(-.3, .3), method="bounded").x
        # part des buts marqués avant la pause : λ_MT = k (λ_dom + λ_ext)
        m = TR.HTHome.notna().values
        lam, htg = (lh + la)[m], (TR.HTHome + TR.HTAway).values[m]
        self.k_ht = minimize_scalar(lambda k: -np.sum(htg * np.log(k * lam) - k * lam), bounds=(.2, .7), method="bounded").x
        return self

    def lambdas(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        Xt = sm.add_constant(df[self.cols], has_constant="add")
        return np.asarray(self.gh.predict(Xt)), np.asarray(self.ga.predict(Xt))

    def grilles(self, df: pd.DataFrame) -> np.ndarray:
        lh, la = self.lambdas(df)
        return np.stack([grille(a, b, self.rho) for a, b in zip(lh, la)])

    def coefficients(self) -> pd.DataFrame:
        return pd.DataFrame({"log λ_dom": self.gh.params.values, "log λ_ext": self.ga.params.values}, index=["constante"] + self.cols)


def pmf_nb(k, mu, alpha):
    """Loi binomiale négative NB2 : moyenne mu, variance mu + alpha·mu² (Poisson si alpha → 0)."""
    if alpha < 1e-6:
        return poisson.pmf(k, mu)
    n = 1 / alpha
    return nbinom.pmf(k, n, n / (n + mu))


class ModeleComptage:
    """Comptage (corners, cartons) : régression de Poisson pondérée pour la moyenne + dispersion binomiale négative."""

    def __init__(self, cols, cible):
        self.cols, self.cible = list(cols), cible

    def fit(self, TR: pd.DataFrame, s_ref: int):
        TR = TR[TR.Season >= C.SAISON_MIN_STATS].dropna(subset=self.cols + [self.cible])
        w, Xa = poids(TR, s_ref), sm.add_constant(TR[self.cols])
        self.glm = sm.GLM(TR[self.cible], Xa, family=sm.families.Poisson(), freq_weights=w).fit()
        mu, y = self.glm.predict(Xa).values, TR[self.cible].values
        self.alpha = minimize_scalar(lambda a: -np.sum(w * np.log(pmf_nb(y, mu, a) + 1e-300)), bounds=(0, 1), method="bounded").x
        return self

    def moyenne(self, df: pd.DataFrame) -> np.ndarray:
        return np.asarray(self.glm.predict(sm.add_constant(df[self.cols], has_constant="add")))

    def loi(self, mu: float, kmax: int = 30) -> np.ndarray:
        p = pmf_nb(np.arange(kmax + 1), mu, self.alpha)
        return p / p.sum()


class ModeleStats:
    """Corners (total + par équipe), cartons jaunes (total + par équipe), cartons rouges (total)."""

    def fit(self, X: pd.DataFrame, s_ref: int):
        X = X.assign(Hc=X.HomeCorners, Ac=X.AwayCorners, Hy=X.HomeYellow, Ay=X.AwayYellow)
        self.m = {nom: ModeleComptage(cols, cible).fit(X, s_ref) for nom, cols, cible in [
            ("corners", C.FE_CORNERS, "c_tot"), ("corners_dom", C.FE_CORNERS, "Hc"), ("corners_ext", C.FE_CORNERS, "Ac"),
            ("jaunes", C.FE_JAUNES, "y_tot"), ("jaunes_dom", C.FE_JAUNES, "Hy"), ("jaunes_ext", C.FE_JAUNES, "Ay"),
            ("rouges", C.FE_ROUGES, "r_tot")]}
        return self

    def predire(self, x: pd.DataFrame) -> dict:
        mu = {k: float(m.moyenne(x)[0]) for k, m in self.m.items()}
        out = {}
        for nom, seuils, s_eq in (("corners", C.SEUILS_CORNERS, C.SEUILS_CORNERS_EQUIPE), ("jaunes", C.SEUILS_JAUNES, C.SEUILS_JAUNES_EQUIPE)):
            p = self.m[nom].loi(mu[nom]); k = np.arange(len(p))
            part = mu[f"{nom}_dom"] / (mu[f"{nom}_dom"] + mu[f"{nom}_ext"])      # répartition cohérente avec le total
            md, me = mu[nom] * part, mu[nom] * (1 - part)
            pd_, pe = self.m[f"{nom}_dom"].loi(md), self.m[f"{nom}_ext"].loi(me)
            out[nom] = {"total": mu[nom], "dom": md, "ext": me, "plus_de": {s: float(p[k > s].sum()) for s in seuils}, "loi": p,
                        "dom_plus_de": {s: float(pd_[k > s].sum()) for s in s_eq}, "ext_plus_de": {s: float(pe[k > s].sum()) for s in s_eq}}
        out["rouges"] = {"total": mu["rouges"], "au_moins_un": float(1 - self.m["rouges"].loi(mu["rouges"])[0])}
        return out


@dataclass
class ModeleComplet:
    m1x2: Modele1X2
    buts: ModeleButs
    s_ref: int
    stats: ModeleStats | None = None

    @classmethod
    def entrainer(cls, X: pd.DataFrame, s_ref: int | None = None, fe=None, fe_b=None, stats=True):
        s_ref = int(X.Season.max()) if s_ref is None else s_ref
        return cls(Modele1X2(fe).fit(X, s_ref), ModeleButs(fe_b).fit(X, s_ref), s_ref, ModeleStats().fit(X, s_ref) if stats else None)
