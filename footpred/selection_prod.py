"""Sélection du jour en production : applique l'artefact appris par scripts/banc_evaluer.py (ensemble, méta-modèle, seuils)
aux matchs à venir publiés par le pipeline. Aucun paramètre n'est réestimé ici.

Pour chaque match d'avant-match : distribution conjointe cohérente (Dixon-Coles repondérée sur les probabilités 1X2 retenues),
17 marchés candidats, probabilité calibrée et borne basse, référence (marché sans marge si coté, sinon fréquence historique),
désaccord entre modèles de base, entropie, qualité des données, explication linéaire du modèle 1X2, puis décision
(retenue / prudente / abstention) selon trois modes (meilleur compromis, plus probable, plus prédictible).
"""
import json
import os

import numpy as np
import pandas as pd

from . import config as C
from . import selection as S
from .banc import FE_E1, _catboost
from .markets import shin
from .models import Modele1X2

ARTEFACT = os.path.join(os.path.dirname(__file__), "artefacts", "selection.json")
LIBELLES_VARIABLES = {
    "dElo": "écart de niveau Elo", "absElo": "écart Elo (valeur absolue)", "dQ": "forme récente (xG proxy, différence)",
    "Otot": "ouverture offensive récente (xG proxy cumulé)", "pi_diff": "écart de pi-rating", "pi_diff_avg": "écart de pi-rating moyen",
    "g_lh": "attaque/défense attendue (rating de buts, domicile)", "g_la": "attaque/défense attendue (rating de buts, extérieur)",
    "lg_SP1": "effet championnat (Liga)", "lg_I1": "effet championnat (Serie A)", "lg_D1": "effet championnat (Bundesliga)", "lg_F1": "effet championnat (Ligue 1)",
    "motiv_h": "enjeu de fin de saison (domicile)", "motiv_a": "enjeu de fin de saison (extérieur)",
    "sansenjeu_h": "domicile sans enjeu", "sansenjeu_a": "extérieur sans enjeu",
}


def charger_artefact(chemin: str = ARTEFACT) -> dict | None:
    if not os.path.exists(chemin):
        return None
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


class MoteurSelection:
    def __init__(self, X: pd.DataFrame, modele_1x2, artefact: dict | None = None, catboost: bool = True):
        """X : variables d'entraînement (toutes saisons jouées) ; modele_1x2 : modèle E0 déjà entraîné du pipeline."""
        self.art = artefact or charger_artefact()
        self.ok = self.art is not None
        if not self.ok:
            return
        s_ref = int(X.Season.max())
        self.e0 = modele_1x2
        self.e1 = Modele1X2(FE_E1).fit(X, s_ref)
        self.e3 = _catboost(X, s_ref, C.FE) if catboost else None
        self.meta = S.MetaModele.depuis(self.art["meta"])
        self.ens = S.Ensemble.depuis(self.art["ensemble_sport"]) if self.art.get("source_1x2") == "ensemble" else None
        self.seuils = self.art["seuils"]
        self.freq = self.art["frequences_marches"]
        self.moyennes = X[list(self.e0.cols)].mean()
        lr = self.e0.lr
        self.coef_h = lr.coef_[0] - lr.coef_[1]          # contribution à log(P1/PX)
        self.coef_a = lr.coef_[2] - lr.coef_[1]          # contribution à log(P2/PX)

    # ------------------------------------------------------------------ explication linéaire (valeurs SHAP exactes d'un modèle linéaire)
    def expliquer(self, x: dict, dom: str, ext: str) -> dict:
        cols = list(self.e0.cols)
        dx = np.array([float(x.get(c, np.nan)) for c in cols]) - self.moyennes.values
        dx = np.nan_to_num(dx)
        ch, ca = self.coef_h * dx, self.coef_a * dx
        lib = lambda c: LIBELLES_VARIABLES.get(c, c)
        dom_v = sorted(((ch[i] - ca[i], lib(c)) for i, c in enumerate(cols)), reverse=True)
        nul_v = sorted(((-(ch[i] + ca[i]) / 2, lib(c)) for i, c in enumerate(cols)), reverse=True)
        fmt = lambda l: [{"variable": n, "effet": round(float(v), 3)} for v, n in l if abs(v) >= 0.02][:3]
        return {"domicile": fmt(dom_v), "exterieur": fmt([(-v, n) for v, n in reversed(dom_v)]), "nul": fmt(nul_v),
                "note": "Contributions du modèle 1X2 linéaire (log-rapports) par rapport à un match moyen : une variable a influencé "
                        "la prédiction du modèle, elle ne « provoque » pas le résultat."}

    # ------------------------------------------------------------------ un match
    def analyser(self, x: dict, M: np.ndarray, odds: dict | None, joues_min, dom: str, ext: str, critiques: dict) -> dict:
        X1 = pd.DataFrame([{c: x.get(c, np.nan) for c in self.e0.cols}])
        complet = bool(np.isfinite(X1.values.astype(float)).all())
        base = {"E0 Goalgebra v5 (logit)": self.e0.predict(X1)[0], "E1 Logistique Elo + forme": self.e1.predict(X1[FE_E1])[0]}
        Mg = np.asarray(M, float)
        base["E2 Dixon-Coles (buts)"] = np.array([np.tril(Mg, -1).sum(), np.trace(Mg), np.triu(Mg, 1).sum()])
        if self.e3 is not None:
            base["E3 CatBoost (sport)"] = self.e3.predict_proba(X1[list(C.FE)])[0]
        p_src = self.ens.predict({k: v[None] for k, v in base.items()})[0] if self.ens is not None else base["E0 Goalgebra v5 (logit)"]
        pm, marge = (None, None)
        if odds and all(odds.get(k) for k in ("home", "draw", "away")):
            pm, marge = shin([odds["home"], odds["draw"], odds["away"]])
        p_over = None
        if odds and odds.get("over25") and odds.get("under25"):
            a, b = 1 / odds["over25"], 1 / odds["under25"]; p_over = a / (a + b)
        ref_m = S.probas_marche_reference(pm, p_over)
        Madj = S.ajuster_grille(Mg, p_src)
        pk = S.probas_marches(Madj)
        par_mod = [S.probas_marches(S.ajuster_grille(Mg, v)) for v in base.values()]
        D = float(S.desaccord(list(base.values())))
        H = float(S.entropie(p_src))
        installee = joues_min is not None and np.isfinite(joues_min) and joues_min >= 5
        cles = list(S.MARCHES)
        fam = [S.MARCHES[k][1] for k in cles]
        p_raw = np.array([pk[k] for k in cles])
        disp = np.array([np.std([S.logit(pm_[k]) for pm_ in par_mod]) for k in cles])
        Z = S.variables_meta(p_raw, fam, np.full(len(cles), D), np.full(len(cles), H), np.full(len(cles), float(installee)),
                             np.full(len(cles), float(pm is not None)))
        p_meta, p_bas = self.meta.predict(Z, disp)
        cote_de = {"home": "home", "draw": "draw", "away": "away", "over25": "over25", "under25": "under25"}
        cands = []
        for j, k in enumerate(cles):
            ref = ref_m.get(k, self.freq[k])
            c = {"cle": k, "marche": S.MARCHES[k][0].format(dom=dom, ext=ext), "famille": fam[j], "p": float(p_meta[j]), "p_bas": float(p_bas[j]),
                 "p_modele": float(p_raw[j]), "ref": float(ref), "ref_source": "marché (sans marge)" if k in ref_m else "fréquence historique",
                 "info": float(S.kl_bits(p_meta[j], ref)), "ecart": float(p_meta[j] - ref)}
            cote = (odds or {}).get(cote_de.get(k, ""), None)
            if cote and cote > 1:
                c.update(cote=float(cote), ev=float(p_meta[j] * cote - 1), ev_prudente=float(p_bas[j] * cote - 1))
            cands.append(c)
        controles = {"horaire fiable": critiques.get("horaire", True), "données à jour": critiques.get("fraicheur", True),
                     "variables complètes": complet, "saison installée (≥ 5 matchs)": bool(installee), "cotes disponibles": pm is not None}
        qualite = 100 * float(np.mean(list(controles.values())))
        qualite_ok = controles["horaire fiable"] and controles["données à jour"] and controles["variables complètes"]
        dec = S.decider(cands, self.seuils, D, qualite_ok, "compromis")
        manquantes = [k for k, v in controles.items() if not v]
        return {"decision": dec["decision"], "choix": dec["choix"], "raisons": dec["raisons"],
                "plus_probable": max(cands, key=lambda c: c["p"]),          # probabilité calibrée maximale, même triviale
                "candidats": sorted(cands, key=lambda c: -c["p"]),
                "modeles": {k: [round(float(z), 4) for z in v] for k, v in base.items()},
                "source_1x2": "ensemble" if self.ens is not None else "E0", "p_1x2": [round(float(z), 4) for z in p_src],
                "marche_1x2": None if pm is None else [round(float(z), 4) for z in pm], "marge": None if marge is None else round(float(marge), 4),
                "desaccord": round(D, 4), "entropie": round(H, 4), "qualite": round(qualite), "controles": controles, "manquantes": manquantes,
                "confiance": round(float(dec["choix"]["p_bas"]), 4) if dec["choix"] else None,
                "scores": [{"score": f"{i}-{j}", "p": round(float(Madj[i, j]), 4)} for i, j in
                           sorted(((i, j) for i in range(Madj.shape[0]) for j in range(Madj.shape[1])), key=lambda t: -Madj[t])[:8]],
                "explication": self.expliquer(x, dom, ext)}
