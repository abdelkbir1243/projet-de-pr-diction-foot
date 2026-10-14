"""Étude « données d'événements » d'après Hassard & Kerr (2024), ISSC 2024, doi:10.1109/ISSC61953.2024.10603147.

Données : StatsBomb Open Data, saison 2015/16 (seule saison complète gratuite pour les grands championnats).
Trois questions :
  A. Reproduction de l'article : variables calculées sur le match lui-même, découpage aléatoire 80/20.
  B. Prédiction honnête avant le match : moyennes des matchs précédents (section V de l'article), évaluation chronologique.
  C. Valeur ajoutée : ces variables améliorent-elles le modèle v5 (prédictions hors échantillon) ?

    python scripts/sb_agg.py data/statsbomb_2015.pkl      # téléchargement et agrégation (~6 Go transférés, ~3 min)
    python scripts/etude_statsbomb.py data/statsbomb_2015.pkl
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from footpred import evaluation as E                                  # noqa: E402
from footpred.data import charger_matchs                               # noqa: E402
from footpred.equipes import associer                                  # noqa: E402
from footpred.features import construire                               # noqa: E402

NX, NY = 12, 8
SORTIE = os.path.join(os.path.dirname(__file__), "..", "results", "tables")


# ---------------------------------------------------------------- expected threat (Singh, 2018)
def _resoudre_xt(shots, goals, moves, T, iterations=30):
    tot = shots + moves
    p_tir, p_dep = shots / np.maximum(tot, 1), moves / np.maximum(tot, 1)
    p_but = goals / np.maximum(shots, 1)
    Tn = T / np.maximum(moves, 1)[:, None]
    xt = np.zeros(len(shots))
    for _ in range(iterations):
        xt = p_tir * p_but + p_dep * (Tn @ xt)
    return xt


def _cumuler(acc, r):
    g = r["grid"]
    for c, v in g["shots"].items(): acc[0][c] += v
    for c, v in g["goals"].items(): acc[1][c] += v
    for c, v in g["moves"].items(): acc[2][c] += v
    for (a, b), v in g["trans"].items(): acc[3][a, b] += v


def grille_xt(res, iterations=30):
    """Grille estimée sur tous les matchs fournis (partie A : reproduction de l'article, variables du match lui-même)."""
    n = NX * NY
    acc = [np.zeros(n), np.zeros(n), np.zeros(n), np.zeros((n, n))]
    for r in res:
        _cumuler(acc, r)
    return _resoudre_xt(*acc, iterations=iterations)


def grilles_xt_anterieures(res, min_matchs=60, iterations=30):
    """Parties B et C, sans fuite : la grille utilisée pour un match n'est estimée que sur les matchs joués AVANT sa date.
    Renvoie {match_id: grille} ; None tant que moins de `min_matchs` matchs antérieurs sont disponibles."""
    n = NX * NY
    acc = [np.zeros(n), np.zeros(n), np.zeros(n), np.zeros((n, n))]
    par_date = {}
    for r in res:
        par_date.setdefault(pd.Timestamp(r["date"]).normalize(), []).append(r)
    out, vus = {}, 0
    for jour in sorted(par_date):
        grille = _resoudre_xt(*acc, iterations=iterations) if vus >= min_matchs else None
        for r in par_date[jour]:
            out[r["match_id"]] = grille
        for r in par_date[jour]:
            _cumuler(acc, r); vus += 1
    return out


# ---------------------------------------------------------------- variables de l'article, par équipe et par match
def _xt_equipe(r, t, xt):
    g = xt.get(r["match_id"]) if isinstance(xt, dict) else xt
    return np.nan if g is None else sum(n * (g[b] - g[a_]) for (a_, b), n in r["moves"][t].items())


def variables(res, xt):
    """`xt` : une grille commune, ou {match_id: grille} (grilles estimées sur les seuls matchs antérieurs)."""
    lignes = []
    for r in res:
        h, a = r["home"], r["away"]
        tot_poss = sum(r["f"][t].get("poss_time", 0) for t in (h, a)) or 1
        att3 = sum(r["f"][t].get("passes_att3", 0) for t in (h, a)) or 1
        for t, o, dom in ((h, a, 1), (a, h, 0)):
            f = r["f"][t]
            v = {"match_id": r["match_id"], "date": pd.Timestamp(r["date"]), "comp": r["comp"], "team": t, "opp": o, "home": dom,
                 "gf": r["hg"] if dom else r["ag"], "ga": r["ag"] if dom else r["hg"],
                 "possession": f.get("poss_time", 0) / tot_poss, "events": f.get("events", 0), "ev_def3": f.get("ev_def3", 0),
                 "ev_att3": f.get("ev_att3", 0), "ev_box": f.get("ev_box", 0), "dist_goal": f.get("dist_goal", 0),
                 "dribbles": f.get("dribbles", 0), "dribble_pct": f.get("dribbles_ok", 0) / max(f.get("dribbles", 0), 1),
                 "carries": f.get("carries", 0), "carry_len": f.get("carry_len", 0) / max(f.get("carries", 0), 1),
                 "passes": f.get("passes", 0), "pass_pct": f.get("passes_ok", 0) / max(f.get("passes", 0), 1),
                 "pass_len": f.get("pass_len", 0) / max(f.get("passes", 0), 1), "passes_att3": f.get("passes_att3", 0),
                 "field_tilt": f.get("passes_att3", 0) / att3, "shots": f.get("shots", 0), "sot": f.get("sot", 0),
                 "sot_pct": f.get("sot", 0) / max(f.get("shots", 0), 1), "xg": f.get("xg", 0),
                 "xt": _xt_equipe(r, t, xt)}
            lignes.append(v)
    return pd.DataFrame(lignes)


FEATS = ["possession", "events", "ev_def3", "ev_att3", "ev_box", "dist_goal", "dribbles", "dribble_pct", "carries", "carry_len",
         "passes", "pass_pct", "pass_len", "passes_att3", "field_tilt", "shots", "sot", "sot_pct", "xg", "xt"]


def matchs(V):
    """Une ligne par match : variables domicile (h_) et extérieur (a_), résultat y (0 = 1, 1 = X, 2 = 2)."""
    H = V[V.home == 1].set_index("match_id"); A = V[V.home == 0].set_index("match_id")
    M = H[["date", "comp", "team", "opp", "gf", "ga"]].rename(columns={"team": "home_team", "opp": "away_team", "gf": "hg", "ga": "ag"})
    M = M.join(H[FEATS].add_prefix("h_")).join(A[FEATS].add_prefix("a_"))
    M["y"] = np.select([M.hg > M.ag, M.hg == M.ag], [0, 1], 2)
    return M.reset_index().sort_values(["date", "match_id"]).reset_index(drop=True)


def glissantes(V):
    """Moyenne des matchs PRÉCÉDENTS de la saison (section V de l'article) : aucune information du match prédit."""
    V = V.sort_values(["team", "date"]).copy()
    for c in FEATS:
        V[f"m_{c}"] = V.groupby("team")[c].transform(lambda s: s.shift(1).expanding().mean())     # NaN ignorés
    return V


def modeles():
    return {"SVM linéaire": make_pipeline(StandardScaler(), SVC(kernel="linear", probability=True, random_state=0)),
            "Random Forest": RandomForestClassifier(500, min_samples_leaf=5, random_state=0),
            "XGBoost": XGBClassifier(n_estimators=1000, learning_rate=0.01, max_depth=3, subsample=0.8, eval_metric="mlogloss", random_state=0),
            "Régression logistique": make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=5000))}


def evaluer(P, y):
    return {"n": len(y), "accuracy": float(np.mean(P.argmax(1) == y)), "log_loss": float(E.log_loss(P, y).mean()),
            "brier": float(E.brier(P, y).mean())}


def chronologique(M, cols, fabrique, debut=8):
    """Chaque semaine est prédite par un modèle entraîné sur toutes les semaines précédentes de la saison."""
    semaine = M.date.dt.to_period("W-SUN")
    P = np.full((len(M), 3), np.nan)
    sem = sorted(semaine.unique())
    for w in sem[debut:]:
        tr, te = (semaine < w).values, (semaine == w).values
        X = M.loc[tr, cols]; ok = X.notna().all(axis=1).values
        mod = fabrique().fit(X[ok], M.y[tr][ok])
        Xt = M.loc[te, cols]
        if len(Xt):
            P[te] = mod.predict_proba(Xt.fillna(Xt.mean()))
    return P


def main(chemin):
    res = pickle.load(open(chemin, "rb"))
    xt = grille_xt(res)
    V = variables(res, xt)
    M = matchs(V)
    sortie = {}

    # ---------- A. reproduction de l'article (variables du match lui-même, 80/20 aléatoire)
    cols = [f"{s}_{c}" for s in "ha" for c in FEATS]
    Xtr, Xte, ytr, yte = train_test_split(M[cols], M.y, test_size=0.2, random_state=42, stratify=M.y)
    A = {}
    for nom, mod in modeles().items():
        A[nom] = evaluer(mod.fit(Xtr, ytr).predict_proba(Xte), yte.values)
    sortie["A_meme_match"] = pd.DataFrame(A).T

    # ---------- B. avant le match : moyennes des matchs précédents, évaluation chronologique
    # xT recalculé avec des grilles estimées uniquement sur les matchs antérieurs (aucune information future)
    V = variables(res, grilles_xt_anterieures(res))
    G = glissantes(V)
    Hm = G[G.home == 1].set_index("match_id")[[f"m_{c}" for c in FEATS]].add_prefix("h_")
    Am = G[G.home == 0].set_index("match_id")[[f"m_{c}" for c in FEATS]].add_prefix("a_")
    MB = M.set_index("match_id").join(Hm).join(Am).reset_index()
    for c in ["xg", "xt", "field_tilt", "shots", "possession"]:
        MB[f"d_{c}"] = MB[f"h_m_{c}"] - MB[f"a_m_{c}"]
    colsB = [c for c in MB if c.startswith(("h_m_", "a_m_"))]

    # rattachement au dataset du projet : Elo, cotes, et probabilités hors échantillon du modèle v5
    raw = charger_matchs()
    d = construire(raw)
    X = d.X[d.X.Season == 2015]
    te5, r5 = E.walk_forward(d.X, [2015])
    v5 = pd.DataFrame(r5["P"], columns=["v5_1", "v5_X", "v5_2"], index=te5.index)
    X = X.join(v5)
    cle = {}
    for lg in X.Division.unique():
        eq = sorted(set(X[X.Division == lg].HomeTeam))
        for t in MB[MB.comp == lg].home_team.unique():
            cle[(lg, t)] = associer(t, eq)
    MB["ds_home"] = [cle.get((c, t)) for c, t in zip(MB.comp, MB.home_team)]
    MB["ds_away"] = [cle.get((c, t)) for c, t in zip(MB.comp, MB.away_team)]
    Xk = X.assign(k=X.MatchDate.dt.strftime("%Y-%m-%d") + X.HomeTeam + X.AwayTeam)
    MB["k"] = MB.date.dt.strftime("%Y-%m-%d") + MB.ds_home.fillna("?") + MB.ds_away.fillna("?")
    MB = MB.merge(Xk[["k", "dElo", "v5_1", "v5_X", "v5_2", "OddHome", "OddDraw", "OddAway"]], on="k", how="left")
    sortie["rattachement"] = pd.DataFrame({"valeur": {"matchs StatsBomb": len(M), "rattachés au dataset": int(MB.v5_1.notna().sum())}})
    MB = MB[MB.v5_1.notna()].reset_index(drop=True)

    PB = {}
    for nom, fab in [("Régression logistique", lambda: modeles()["Régression logistique"]), ("XGBoost", lambda: modeles()["XGBoost"])]:
        PB[f"{nom} (événements)"] = chronologique(MB, colsB, fab)
    PB["Régression logistique (Elo seul)"] = chronologique(MB, ["dElo"], lambda: LogisticRegression(max_iter=2000))
    ok = ~np.isnan(PB["Régression logistique (événements)"]).any(axis=1)
    y = MB.y.values[ok]
    lignes = {k: evaluer(P[ok], y) for k, P in PB.items()}
    lignes["Modèle v5 (hors échantillon)"] = evaluer(MB[["v5_1", "v5_X", "v5_2"]].values[ok], y)
    Pm = E.proba_cotes(MB)[ok]; okm = ~np.isnan(Pm).any(axis=1)
    lignes["Cotes des bookmakers"] = evaluer(Pm[okm], y[okm])
    sortie["B_avant_match"] = pd.DataFrame(lignes).T

    # ---------- C. valeur ajoutée au modèle v5 (empilement, évaluation chronologique, mêmes matchs)
    lv = np.log(MB[["v5_1", "v5_X", "v5_2"]].values)
    MB["lv1"], MB["lv2"] = lv[:, 0] - lv[:, 1], lv[:, 2] - lv[:, 1]
    base = ["lv1", "lv2"]
    extra = {"+ xG": ["d_xg"], "+ xT": ["d_xt"], "+ field tilt": ["d_field_tilt"], "+ xG, xT, field tilt, tirs, possession": [f"d_{c}" for c in ["xg", "xt", "field_tilt", "shots", "possession"]]}
    fab = lambda: make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=5000))
    P0 = chronologique(MB, base, fab)
    okc = ~np.isnan(P0).any(axis=1)
    l0 = E.log_loss(P0[okc], MB.y.values[okc])
    C = {"v5 recalibré (référence)": {**evaluer(P0[okc], MB.y.values[okc]), "écart_logloss_e3": 0.0, "ic_bas": 0.0, "ic_haut": 0.0}}
    for nom, cs in extra.items():
        P = chronologique(MB, base + cs, fab)
        l = E.log_loss(P[okc], MB.y.values[okc]); ic = E.ic_bootstrap(l - l0)
        C[f"v5 {nom}"] = {**evaluer(P[okc], MB.y.values[okc]), "écart_logloss_e3": 1e3 * float((l - l0).mean()), "ic_bas": 1e3 * ic[0], "ic_haut": 1e3 * ic[1]}
    sortie["C_valeur_ajoutee"] = pd.DataFrame(C).T

    # corrélations avec le résultat (cf. figure 5 de l'article) : variables du match vs moyennes d'avant-match
    win = (M.y == 0).astype(float)
    corr = {c: {"même match": np.corrcoef(M[f"h_{c}"], win)[0, 1],
                "avant le match": MB[[f"h_m_{c}"]].assign(w=(MB.y == 0).astype(float)).dropna().corr().iloc[0, 1]} for c in FEATS}
    sortie["correlations_victoire_domicile"] = pd.DataFrame(corr).T.sort_values("même match", ascending=False)

    os.makedirs(SORTIE, exist_ok=True)
    for k, t in sortie.items():
        t.round(4).to_csv(os.path.join(SORTIE, f"statsbomb_2015_{k}.csv"))
        print(f"\n=== {k}\n{t.round(4).to_string()}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/statsbomb_2015.pkl")
