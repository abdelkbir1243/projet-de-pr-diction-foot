"""Moteur de confiance et de sélection (« Sélection du jour »).

Principes (docs/selection.md) :
  1. Distribution conjointe unique. La matrice des scores Dixon-Coles est repondérée pour que ses probabilités 1X2 égalent celles
     de l'ensemble calibré ; tous les marchés (double chance, remboursé si nul, plus/moins de buts, les deux marquent, chaque équipe
     marque) en sont dérivés : aucune contradiction possible entre marchés.
  2. Ensemble appris, pas moyenné. Empilement log-linéaire (régression multinomiale sur les log-rapports des modèles de base),
     entraîné uniquement sur des prédictions hors échantillon de saisons antérieures.
  3. Probabilité, confiance et qualité sont distinctes. Un méta-modèle (appris sur la fenêtre de validation) estime la probabilité
     qu'une sélection soit correcte selon sa probabilité, sa famille de marché, le désaccord entre modèles, l'entropie et la
     qualité des données ; la borne basse combine l'incertitude de ce méta-modèle et la dispersion des modèles de base.
  4. Valeur informative. Le « meilleur compromis » maximise l'information apportée par rapport à la meilleure référence disponible
     (probabilité du marché sans marge si une cote existe, sinon fréquence historique du marché), en bits (divergence de
     Kullback-Leibler) : « plus de 0,5 but à 93 % » quand la fréquence historique est 92 % n'apporte presque rien.
  5. Abstention. Les seuils (borne basse, désaccord, information minimale) sont choisis sur la fenêtre de validation ; une
     abstention est une sortie normale.
Aucun coefficient n'est fixé à la main : tout ce qui pondère est estimé sur des données antérieures à la période évaluée.
"""
import math

import numpy as np

Z_UNILATERAL = 1.6449            # quantile 95 % unilatéral (borne basse)

# clé → (libellé, famille). Les libellés {dom}/{ext} sont remplacés par les noms des équipes.
MARCHES = {
    "home": ("Victoire {dom}", "Résultat"), "draw": ("Match nul", "Résultat"), "away": ("Victoire {ext}", "Résultat"),
    "dc_1x": ("{dom} ou nul", "Double chance"), "dc_x2": ("Nul ou {ext}", "Double chance"), "dc_12": ("{dom} ou {ext} (pas de nul)", "Double chance"),
    "dnb_home": ("{dom} (remboursé si nul)", "Remboursé si nul"), "dnb_away": ("{ext} (remboursé si nul)", "Remboursé si nul"),
    "over05": ("Plus de 0,5 but", "Buts"), "over15": ("Plus de 1,5 but", "Buts"), "over25": ("Plus de 2,5 buts", "Buts"),
    "under25": ("Moins de 2,5 buts", "Buts"), "under35": ("Moins de 3,5 buts", "Buts"),
    "btts_yes": ("Les deux équipes marquent", "Les deux marquent"), "btts_no": ("Au moins une équipe ne marque pas", "Les deux marquent"),
    "home_scores": ("{dom} marque au moins un but", "Équipe marque"), "away_scores": ("{ext} marque au moins un but", "Équipe marque"),
}
FAMILLES = sorted({f for _, f in MARCHES.values()})


# ---------------------------------------------------------------- distribution conjointe cohérente
def regions(gmax: int = 10):
    G = np.arange(gmax + 1)
    d = G[:, None] - G[None, :]
    return d > 0, d == 0, d < 0


def ajuster_grille(M: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Repondère la matrice des scores pour que P(1), P(X), P(2) égalent p, en conservant la forme des scores dans chaque issue."""
    M, p = np.asarray(M, float), np.asarray(p, float)
    out = M.copy()
    for k, r in enumerate(regions(M.shape[-1] - 1)):
        if M.ndim == 3:
            f = p[:, k] / np.maximum(M[:, r].sum(1), 1e-12)
            out[:, r] = M[:, r] * f[:, None]
        else:
            out[r] = M[r] * (p[k] / max(M[r].sum(), 1e-12))
    return out


def probas_marches(M: np.ndarray) -> dict:
    """Probabilités de tous les marchés candidats, dérivées d'une même matrice (ou d'une pile de matrices (n, g, g))."""
    M = np.asarray(M, float)
    if M.ndim == 2:
        return {k: float(v[0]) for k, v in probas_marches(M[None]).items()}
    g = M.shape[-1]; G = np.arange(g); tot = G[:, None] + G[None, :]
    hw, dr, aw = regions(g - 1)
    p1, px, p2 = M[:, hw].sum(1), M[:, dr].sum(1), M[:, aw].sum(1)
    som = lambda masque: M[:, masque].sum(1)
    return {"home": p1, "draw": px, "away": p2, "dc_1x": p1 + px, "dc_x2": px + p2, "dc_12": p1 + p2,
            "dnb_home": p1 / np.maximum(p1 + p2, 1e-12), "dnb_away": p2 / np.maximum(p1 + p2, 1e-12),
            "over05": som(tot > 0.5), "over15": som(tot > 1.5), "over25": som(tot > 2.5), "under25": som(tot < 2.5), "under35": som(tot < 3.5),
            "btts_yes": M[:, 1:, 1:].sum((1, 2)), "btts_no": 1 - M[:, 1:, 1:].sum((1, 2)),
            "home_scores": M[:, 1:, :].sum((1, 2)), "away_scores": M[:, :, 1:].sum((1, 2))}


def issue(cle: str, h: int, a: int):
    """Résultat observé d'un marché : 1 réussi, 0 raté, None si sans objet (remboursé si nul et match nul)."""
    t = h + a
    r = {"home": h > a, "draw": h == a, "away": h < a, "dc_1x": h >= a, "dc_x2": h <= a, "dc_12": h != a,
         "dnb_home": None if h == a else h > a, "dnb_away": None if h == a else h < a,
         "over05": t > 0.5, "over15": t > 1.5, "over25": t > 2.5, "under25": t < 2.5, "under35": t < 3.5,
         "btts_yes": h > 0 and a > 0, "btts_no": not (h > 0 and a > 0), "home_scores": h > 0, "away_scores": a > 0}[cle]
    return None if r is None else int(r)


def probas_marche_reference(pm: np.ndarray | None, p_over25: float | None) -> dict:
    """Probabilités du marché (sans marge) pour les marchés dérivables des cotes réellement cotées (1X2, plus/moins 2,5)."""
    out = {}
    if pm is not None and np.all(np.isfinite(pm)):
        p1, px, p2 = pm
        out.update(home=p1, draw=px, away=p2, dc_1x=p1 + px, dc_x2=px + p2, dc_12=p1 + p2, dnb_home=p1 / (p1 + p2), dnb_away=p2 / (p1 + p2))
    if p_over25 is not None and np.isfinite(p_over25):
        out.update(over25=p_over25, under25=1 - p_over25)
    return out


# ---------------------------------------------------------------- incertitude et accord
def entropie(p: np.ndarray) -> np.ndarray:
    """Entropie normalisée de la distribution 1X2 (0 = certaine, 1 = uniforme)."""
    p = np.clip(np.asarray(p, float), 1e-12, 1)
    return -(p * np.log(p)).sum(-1) / math.log(p.shape[-1])


def desaccord(probas: list) -> np.ndarray:
    """Plus grande distance en variation totale entre deux modèles de base (0 = identiques, 1 = opposés)."""
    P = [np.asarray(x, float) for x in probas]
    d = np.zeros(P[0].shape[:-1])
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            d = np.maximum(d, 0.5 * np.abs(P[i] - P[j]).sum(-1))
    return d


def kl_bits(p, b) -> np.ndarray:
    """Information (bits) d'une probabilité p par rapport à une référence b, pour un événement binaire."""
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9); b = np.clip(np.asarray(b, float), 1e-9, 1 - 1e-9)
    return (p * np.log2(p / b) + (1 - p) * np.log2((1 - p) / (1 - b)))


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def expit(x):
    return 1 / (1 + np.exp(-np.asarray(x, float)))


# ---------------------------------------------------------------- ensemble (empilement log-linéaire)
def variables_empilement(probas: list) -> np.ndarray:
    """Log-rapports log(P1/PX), log(P2/PX) de chaque modèle de base."""
    cols = []
    for P in probas:
        P = np.clip(np.asarray(P, float), 1e-9, 1)
        cols += [np.log(P[:, 0] / P[:, 1]), np.log(P[:, 2] / P[:, 1])]
    return np.column_stack(cols)


class Ensemble:
    """Régression multinomiale sur les log-rapports des modèles de base (empilement + calibration en une étape)."""

    def __init__(self, modeles: list[str], C: float = 1.0):
        self.modeles, self.C = list(modeles), C

    def fit(self, P: dict, y: np.ndarray, masque=None):
        from sklearn.linear_model import LogisticRegression
        X = variables_empilement([P[k] for k in self.modeles])
        m = np.isfinite(X).all(1) if masque is None else masque & np.isfinite(X).all(1)
        self.lr = LogisticRegression(C=self.C, max_iter=5000).fit(X[m], y[m])
        return self

    def predict(self, P: dict) -> np.ndarray:
        X = variables_empilement([P[k] for k in self.modeles])
        out = np.full((len(X), 3), np.nan)
        ok = np.isfinite(X).all(1)
        out[ok] = self.lr.predict_proba(X[ok])
        return out

    def etat(self) -> dict:
        return {"modeles": self.modeles, "C": self.C, "coef": self.lr.coef_.tolist(), "intercept": self.lr.intercept_.tolist(),
                "classes": self.lr.classes_.tolist()}

    @classmethod
    def depuis(cls, e: dict):
        from sklearn.linear_model import LogisticRegression
        o = cls(e["modeles"], e["C"]); o.lr = LogisticRegression()
        o.lr.coef_, o.lr.intercept_, o.lr.classes_ = np.array(e["coef"]), np.array(e["intercept"]), np.array(e["classes"])
        return o


# ---------------------------------------------------------------- méta-modèle : probabilité qu'une sélection soit correcte
def variables_meta(p, famille: list, D, H, installee, cotes) -> np.ndarray:
    """Variables du méta-modèle, dans un ordre fixe : constante, logit(p), familles (référence : Résultat), désaccord, entropie,
    saison installée (≥ 5 matchs joués par les deux équipes), cotes disponibles."""
    p = np.asarray(p, float)
    cols = [np.ones_like(p), logit(p)]
    fam = np.asarray(famille)
    cols += [(fam == f).astype(float) for f in FAMILLES if f != "Résultat"]
    cols += [np.asarray(D, float), np.asarray(H, float), np.asarray(installee, float), np.asarray(cotes, float)]
    return np.column_stack(cols)


NOMS_META = ["constante", "logit(p)"] + [f"famille {f}" for f in FAMILLES if f != "Résultat"] + ["désaccord", "entropie", "saison installée", "cotes disponibles"]


class MetaModele:
    """Régression logistique (statsmodels) : P(sélection correcte | p, famille, désaccord, entropie, qualité) et sa covariance."""

    def fit(self, Z: np.ndarray, y: np.ndarray):
        """Les variables constantes dans l'échantillon (ex. cotes toujours disponibles) sont retirées : coefficient 0, sans variance."""
        import statsmodels.api as sm
        # variable binaire presque constante (ex. cotes disponibles dans 99,9 % des matchs) : effet non estimable, retirée
        minorite = np.array([min((c > 0.5).mean(), (c <= 0.5).mean()) if set(np.unique(c)) <= {0.0, 1.0} else 1.0 for c in Z[:, 1:].T])
        garde = np.r_[True, (Z[:, 1:].std(0) > 1e-9) & (minorite >= 0.02)]
        r = sm.Logit(y, Z[:, garde]).fit(disp=0, maxiter=200)
        k = Z.shape[1]
        self.beta = np.zeros(k); self.beta[garde] = np.asarray(r.params)
        self.cov = np.zeros((k, k)); self.cov[np.ix_(garde, garde)] = np.asarray(r.cov_params())
        return self

    def predict(self, Z: np.ndarray, dispersion_logit=None) -> tuple[np.ndarray, np.ndarray]:
        """Renvoie (probabilité, borne basse unilatérale à 95 %). La borne combine l'incertitude du méta-modèle et la
        dispersion des modèles de base (écart-type de leurs logits pour ce marché)."""
        eta = Z @ self.beta
        se = np.sqrt(np.einsum("ij,jk,ik->i", Z, self.cov, Z))
        if dispersion_logit is not None:
            se = np.sqrt(se ** 2 + np.asarray(dispersion_logit, float) ** 2)
        return expit(eta), expit(eta - Z_UNILATERAL * se)

    def etat(self) -> dict:
        return {"beta": self.beta.tolist(), "cov": self.cov.tolist(), "noms": NOMS_META}

    @classmethod
    def depuis(cls, e: dict):
        o = cls(); o.beta, o.cov = np.array(e["beta"]), np.array(e["cov"])
        return o


# ---------------------------------------------------------------- décision
def decider(cands: list[dict], seuils: dict, desacc: float, qualite_ok: bool, mode: str = "compromis") -> dict:
    """cands : [{cle, p (calibrée), p_bas, ref, info, ...}]. Renvoie {decision, choix, raisons}.

    Une sélection doit être informative : information ≥ κ (bits) par rapport à la référence (marché sans marge si coté, sinon
    fréquence historique du marché) — « plus de 0,5 but à 93 % » n'apporte rien quand la fréquence est 92 %.
      retenue  : informative, borne basse ≥ τ_retenue ET supérieure à la référence, désaccord ≤ δ, qualité suffisante ;
      prudente : informative, probabilité ≥ τ_prudente et supérieure à la référence, sans remplir les conditions précédentes ;
      abstention sinon.
    Choix dans le match — compromis : gain attendu maximal p − référence (succès en plus de la référence) ;
    probable : probabilité maximale."""
    raisons = []
    if not qualite_ok:
        raisons.append("qualité des données insuffisante")
    if desacc > seuils["desaccord_max"]:
        raisons.append(f"désaccord entre modèles élevé ({desacc:.2f} > {seuils['desaccord_max']:.2f})")
    cle_tri = (lambda c: c["p"]) if mode == "probable" else (lambda c: c["p"] - c["ref"])
    informatifs = [c for c in cands if c["info"] >= seuils["info_min"]]
    if not informatifs:
        raisons.append("aucune sélection n'apporte d'information par rapport à la référence")
    admis = [c for c in informatifs if c["p_bas"] >= seuils["p_bas_min"] and c["p_bas"] > c["ref"]]   # même la borne basse bat la référence
    if admis and not raisons:
        return {"decision": "retenue", "choix": max(admis, key=cle_tri), "raisons": []}
    if informatifs and not admis:
        raisons.append(f"aucune sélection informative avec une borne basse ≥ {seuils['p_bas_min']:.0%}")
    prud = [c for c in informatifs if c["p"] >= seuils["p_prudente_min"] and c["p"] > c["ref"]]
    if prud and qualite_ok:
        return {"decision": "prudente", "choix": max(prud, key=cle_tri), "raisons": raisons}
    return {"decision": "abstention", "choix": None, "raisons": raisons or ["probabilités trop proches de la référence"]}
