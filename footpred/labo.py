"""Laboratoire de test : tableaux et graphiques pour le rapport.

    validation(d)            walk-forward 2021-2026 : fréquences, Elo seul, v3, v4, cotes (+ IC bootstrap)
    saison(d, 2025)          une saison prédite par des modèles figés au 1er juillet
    hebdo(d, 2025)           la même saison rejouée semaine par semaine (ré-entraînement chaque lundi)
    strategies(d)            test d'efficience du marché : stratégies de paris simulées (aucune n'est recommandée)
Chaque fonction renvoie un dict de DataFrames ; `enregistrer(res, dossier)` les écrit en CSV.
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from . import config as C
from . import evaluation as E

COUL = {"v4": "#2a78d6", "v3": "#eb6834", "Elo seul": "#1baf7a", "Cotes": "#52514e", "v4 figé": "#86b6ef"}
FE_ELO = ["dElo", "absElo"]
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e6e3",
                     "grid.linewidth": .6, "axes.edgecolor": "#b5b4ae", "font.size": 10})


def _modeles(X, saisons):
    """Prédictions walk-forward des modèles comparés, alignées sur les mêmes matchs."""
    te, v4 = E.walk_forward(X, saisons)
    _, v3 = E.walk_forward(X, saisons, C.FE_V3, C.FE_B_V3)
    _, elo = E.walk_forward(X, saisons, FE_ELO, FE_ELO)
    y = te.y.values
    freq = np.zeros((len(te), 3))
    for s in saisons:
        TR = X[X.Season < s]; w = 0.5 ** ((s - 1 - TR.Season) / C.DEMI_VIE)
        f = np.bincount(TR.y, weights=w, minlength=3); freq[(te.Season == s).values] = f / f.sum()
    return te, y, {"Fréquences": {"P": freq}, "Elo seul": elo, "v3": v3, "v4": v4, "Cotes": {"P": E.proba_cotes(te)}}


def _tableaux(te, y, R, ref="v3"):
    ok = ~np.isnan(R["Cotes"]["P"]).any(1)
    T = pd.DataFrame({k: E.resume(r["P"][ok], y[ok]) for k, r in R.items()}).T
    T.insert(0, "matchs", int(ok.sum()))
    T["skill vs fréquences"] = 1 - T["log loss"] / T.loc["Fréquences", "log loss"]
    ll = {k: E.log_loss(np.nan_to_num(r["P"], nan=1 / 3), y) for k, r in R.items()}
    tests = []
    for a, b in (("v4", ref), ("v4", "Elo seul"), ("v4", "Cotes")):
        d = (ll[a] - ll[b])[ok]; lo, hi = E.ic_bootstrap(d)
        tests.append({"comparaison": f"{a} − {b}", "Δ log loss ×1e3": 1000 * d.mean(), "IC bas": 1000 * lo, "IC haut": 1000 * hi,
                      "significatif": bool(hi < 0 or lo > 0)})
    ov = (te.FTHome + te.FTAway > 2.5).values; bt = ((te.FTHome > 0) & (te.FTAway > 0)).values
    pm = ((1 / te.Over25) / (1 / te.Over25 + 1 / te.Under25)).values; okm = ~np.isnan(pm)
    B = pd.DataFrame({k: {"LL score exact": -np.log(R[k]["p_score"]).mean(), "LL over 2,5": E.log_loss_binaire(R[k]["over25"], ov).mean(),
                          "LL BTTS": E.log_loss_binaire(R[k]["btts"], bt).mean(), "buts prévus/match": (R[k]["lh"] + R[k]["la"]).mean()}
                      for k in ["v3", "v4"]}).T
    B.loc["Cotes"] = [np.nan, E.log_loss_binaire(pm[okm], ov[okm]).mean(), np.nan, np.nan]
    B.loc["Réel"] = [np.nan, np.nan, np.nan, (te.FTHome + te.FTAway).mean()]
    d = (-np.log(R["v4"]["p_score"]) + np.log(R["v3"]["p_score"])); lo, hi = E.ic_bootstrap(d)
    d2 = E.log_loss_binaire(R["v4"]["over25"], ov) - E.log_loss_binaire(R["v3"]["over25"], ov); lo2, hi2 = E.ic_bootstrap(d2)
    tests += [{"comparaison": "v4 − v3 (score exact)", "Δ log loss ×1e3": 1000 * d.mean(), "IC bas": 1000 * lo, "IC haut": 1000 * hi, "significatif": bool(hi < 0 or lo > 0)},
              {"comparaison": "v4 − v3 (over 2,5)", "Δ log loss ×1e3": 1000 * d2.mean(), "IC bas": 1000 * lo2, "IC haut": 1000 * hi2, "significatif": bool(hi2 < 0 or lo2 > 0)}]
    lig = pd.DataFrame({k: pd.Series(ll[k][ok], index=te.index[ok]).groupby(te.Division[ok].map(C.LIGUES)).mean() for k in ["Elo seul", "v3", "v4", "Cotes"]})
    sai = pd.DataFrame({k: pd.Series(ll[k][ok], index=te.index[ok]).groupby(te.Season[ok]).mean() for k in ["Elo seul", "v3", "v4", "Cotes"]})
    return {"1X2": T, "tests": pd.DataFrame(tests).set_index("comparaison"), "buts": B, "par_ligue": lig, "par_saison": sai}, ll, ok


def validation(d, saisons=C.SAISONS_TEST, figure=True):
    te, y, R = _modeles(d.X, saisons)
    res, ll, ok = _tableaux(te, y, R)
    if figure:
        res["_fig"] = _figure_saison(te, y, R, ll, ok, res["par_ligue"], f"Test walk-forward {saisons[0]}/{saisons[0] + 1 - 2000:02d} → {saisons[-1]}/{saisons[-1] + 1 - 2000:02d}")
    res["_pred"] = te.assign(P1=R["v4"]["P"][:, 0], PX=R["v4"]["P"][:, 1], P2=R["v4"]["P"][:, 2], LL_v4=ll["v4"], LL_cotes=np.where(ok, ll["Cotes"], np.nan))
    return res


def saison(d, s=2025, ligues=None, figure=True):
    X = d.X if ligues is None else d.X[d.X.Division.isin(ligues) | (d.X.Season < s)]
    res = validation(type("D", (), {"X": X})(), [s], figure)
    P = res["_pred"]; P["p_résultat"] = P[["P1", "PX", "P2"]].values[np.arange(len(P)), P.y.values]
    sur = P.nsmallest(10, "p_résultat")
    res["surprises"] = sur.assign(Date=sur.MatchDate.dt.date, Ligue=sur.Division.map(C.LIGUES),
                                  Score=sur.FTHome.astype(int).astype(str) + "-" + sur.FTAway.astype(int).astype(str))[
        ["Date", "Ligue", "HomeTeam", "AwayTeam", "Score", "P1", "PX", "P2", "p_résultat"]].round(3).reset_index(drop=True)
    return res


def hebdo(d, s=2025, ligues=None, figure=True):
    te, r = E.saison_hebdo(d.X, s, ligues)
    y = te.y.values
    P_fige = E.predire_bloc(d.X[d.X.Season < s], te, s - 1)["P"]          # modèle figé au 1er juillet
    Pm = E.proba_cotes(te); ok = ~np.isnan(Pm).any(1)
    S = te.assign(LL_hebdo=E.log_loss(r["P"], y), LL_fige=E.log_loss(P_fige, y), LL_cotes=np.where(ok, E.log_loss(np.nan_to_num(Pm, nan=1 / 3), y), np.nan),
                  juste=r["P"].argmax(1) == y, juste_cotes=np.nan_to_num(Pm).argmax(1) == y)
    g = S.groupby("semaine")
    W = g.agg(matchs=("y", "size"), LL_v4_hebdo=("LL_hebdo", "mean"), LL_v4_fige=("LL_fige", "mean"), LL_cotes=("LL_cotes", "mean"),
              justes_v4=("juste", "mean"), justes_cotes=("juste_cotes", "mean"))
    for c, k in (("LL_hebdo", "cumul_v4_hebdo"), ("LL_fige", "cumul_v4_fige"), ("LL_cotes", "cumul_cotes")):
        W[k] = g[c].sum().cumsum() / g.size().cumsum()
    lo, hi = E.ic_bootstrap(S.LL_hebdo - S.LL_fige); lo2, hi2 = E.ic_bootstrap((S.LL_hebdo - S.LL_cotes)[ok])
    resume = pd.DataFrame({"valeur": {"log loss v4 ré-entraîné chaque semaine": S.LL_hebdo.mean(), "log loss v4 figé": S.LL_fige.mean(),
                                      "log loss cotes": S.LL_cotes.mean(), "gain ré-entraînement ×1e3": 1000 * (S.LL_hebdo - S.LL_fige).mean(),
                                      "IC bas": 1000 * lo, "IC haut": 1000 * hi, "écart v4 − cotes ×1e3": 1000 * (S.LL_hebdo - S.LL_cotes).mean(),
                                      "IC bas (cotes)": 1000 * lo2, "IC haut (cotes)": 1000 * hi2,
                                      "semaines où v4 bat les cotes": float(np.mean(W.LL_v4_hebdo < W.LL_cotes))}})
    W.index = pd.to_datetime(W.index).date; W.index.name = "semaine du"
    res = {"resume": resume, "semaines": W}
    if figure:
        fig, ax = plt.subplots(1, 2, figsize=(16, 4.6)); xw = pd.to_datetime(W.index)
        for c, nom, col, ls in (("cumul_v4_hebdo", "v4 ré-entraîné chaque semaine", COUL["v4"], "-"), ("cumul_v4_fige", "v4 figé", COUL["v4 figé"], "-"),
                                ("cumul_cotes", "Cotes", COUL["Cotes"], "--")):
            ax[0].plot(xw, W[c], lw=2, color=col, ls=ls, label=f"{nom} (final {W[c].iloc[-1]:.3f})")
        ax[0].set_title("Log loss cumulée, semaine après semaine", loc="left", fontsize=11); ax[0].legend(frameon=False, loc="lower right"); ax[0].tick_params(axis="x", rotation=30)
        diff = (W.LL_v4_hebdo - W.LL_cotes).values
        ax[1].bar(xw, diff, width=5, color=np.where(diff < 0, COUL["v4"], "#b5b4ae")); ax[1].axhline(0, color="#52514e", lw=1)
        ax[1].set_title("Écart hebdomadaire v4 − cotes (bleu : v4 meilleur)", loc="left", fontsize=11); ax[1].tick_params(axis="x", rotation=30)
        plt.tight_layout(); res["_fig"] = fig
    return res


def strategies(d, saisons=C.SAISONS_TEST):
    """Rendement moyen par pari (mise 1) de stratégies simulées, avec IC 95 %. Objectif : tester l'efficience du marché."""
    te, r = E.walk_forward(d.X, saisons)
    y = te.y.values; O = te[["OddHome", "OddDraw", "OddAway"]].values; MX = te[["MaxHome", "MaxDraw", "MaxAway"]].values
    Pm = E.proba_cotes(te); win = np.eye(3)[y].astype(bool); P = r["P"]; n = len(y)
    lignes = []
    def bt(masque, cotes, nom):
        masque = masque & np.isfinite(cotes); g = np.where(win, cotes - 1, -1)[masque]
        if len(g) == 0: return
        lo, hi = E.ic_bootstrap(g)
        lignes.append({"stratégie": nom, "paris": len(g), "gagnés": np.mean(g > 0), "rendement": g.mean(), "IC bas": lo, "IC haut": hi})
    for th in (0, .05, .10, .20):
        bt(P * O > 1 + th, O, f"value v4 vs cote moyenne, seuil {th:.0%}")
    for th in (0, .05):
        bt(P * MX > 1 + th, MX, f"value v4 vs meilleure cote, seuil {th:.0%}")
    bt(np.eye(3)[np.nan_to_num(O, nan=99).argmin(1)].astype(bool), O, "toujours le favori")
    bt(np.tile([False, True, False], (n, 1)), O, "toujours le nul")
    bt(np.eye(3)[np.nan_to_num(O, nan=0).argmax(1)].astype(bool), O, "toujours l'outsider")
    return {"strategies": pd.DataFrame(lignes).set_index("stratégie")}


def stats_match(d, saisons=C.SAISONS_TEST):
    """Corners, cartons jaunes et rouges : test walk-forward contre une référence « moyenne de la ligue »."""
    from .models import ModeleComptage
    X = d.X
    lignes, calib = [], []
    for nom, cible, cols, seuil in (("corners", "c_tot", C.FE_CORNERS, 9.5), ("cartons jaunes", "y_tot", C.FE_JAUNES, 4.5),
                                    ("cartons rouges", "r_tot", C.FE_ROUGES, 0.5)):
        ref = cols[0]                                       # l_lg_* : niveau moyen de la ligue
        res = {}
        for version, cc in (("ligue seule", [ref]), ("modèle", cols)):
            parts = []
            for s in saisons:
                TE = X[X.Season == s].dropna(subset=cols + [cible])
                m = ModeleComptage(cc, cible).fit(X[X.Season < s], s - 1)
                mu = m.moyenne(TE); y = TE[cible].values.astype(int)
                P = np.stack([m.loi(u, 40) for u in mu]); k = np.arange(P.shape[1])
                parts.append(pd.DataFrame({"ll": -np.log(P[np.arange(len(y)), np.minimum(y, 40)] + 1e-300), "p_over": P[:, k > seuil].sum(1),
                                           "over": y > seuil, "mu": mu, "y": y}, index=TE.index))
            res[version] = pd.concat(parts)
        idx = res["ligue seule"].index.intersection(res["modèle"].index)
        a, b = res["modèle"].loc[idx], res["ligue seule"].loc[idx]
        lo, hi = E.ic_bootstrap((a.ll - b.ll).values)
        lignes.append({"statistique": nom, "matchs": len(idx), "moyenne réelle": a.y.mean(), "LL ligue seule": b.ll.mean(), "LL modèle": a.ll.mean(),
                       "Δ ×1e3": 1000 * (a.ll - b.ll).mean(), "IC bas": 1000 * lo, "IC haut": 1000 * hi,
                       f"LL over (seuil)": E.log_loss_binaire(a.p_over.values, a.over.values).mean(), "seuil": seuil,
                       "corrélation prévu/réel": np.corrcoef(a.mu, a.y)[0, 1]})
        q = a.groupby(pd.qcut(a.p_over, 5, duplicates="drop"), observed=True)[["p_over", "over"]].mean()
        calib += [{"statistique": f"{nom} +{seuil:g}", "prévu": r.p_over, "observé": r.over} for r in q.itertuples()]
    return {"stats_match": pd.DataFrame(lignes).set_index("statistique"), "calibration_stats": pd.DataFrame(calib)}


def probas_bloc(mc, TE):
    """Probabilités de tous les marchés pour un bloc de matchs (format identique à Predicteur.predire, en vectoriel)."""
    from .models import pmf_nb
    P = mc.m1x2.predict(TE); Ms = mc.buts.grilles(TE)
    G = np.arange(Ms.shape[1]); tot = G[:, None] + G[None, :]
    r = {"1": P[:, 0], "X": P[:, 1], "2": P[:, 2], "btts": Ms[:, 1:, 1:].sum((1, 2)), "cs_dom": Ms[:, :, 0].sum(1), "cs_ext": Ms[:, 0, :].sum(1),
         **{k: (Ms * (tot > s)).sum((1, 2)) for k, s in (("over15", 1.5), ("over25", 2.5), ("over35", 3.5))}}
    if mc.stats is not None:
        mu = {k: m.moyenne(TE) for k, m in mc.stats.m.items()}; k = np.arange(41)
        loi = lambda nom, m: (lambda q: q / q.sum(1, keepdims=True))(pmf_nb(k[None, :], m[:, None], mc.stats.m[nom].alpha))
        for nom, seuils, s_eq in (("corners", C.SEUILS_CORNERS, C.SEUILS_CORNERS_EQUIPE), ("jaunes", C.SEUILS_JAUNES, C.SEUILS_JAUNES_EQUIPE)):
            part = mu[f"{nom}_dom"] / (mu[f"{nom}_dom"] + mu[f"{nom}_ext"])
            Lt, Ld, Le = loi(nom, mu[nom]), loi(f"{nom}_dom", mu[nom] * part), loi(f"{nom}_ext", mu[nom] * (1 - part))
            r[nom] = {"plus_de": {s: Lt[:, k > s].sum(1) for s in seuils}, "dom_plus_de": {s: Ld[:, k > s].sum(1) for s in s_eq},
                      "ext_plus_de": {s: Le[:, k > s].sum(1) for s in s_eq}}
        r["rouges"] = {"au_moins_un": 1 - loi("rouges", mu["rouges"])[:, 0]}
    return r


def fiabilite_decisions(d, saisons=C.SAISONS_TEST):
    """Les paliers de risque tiennent-ils leurs promesses ? Test walk-forward sur tous les marchés de tous les matchs."""
    from .models import ModeleComplet
    from .decision import definitions, palier
    X = d.X; lignes = []
    besoin = sorted(set(C.FE_CORNERS + C.FE_JAUNES + C.FE_ROUGES) | {"HomeCorners", "AwayCorners", "HomeYellow", "AwayYellow", "HomeRed", "AwayRed"})
    for s in saisons:
        TE = X[X.Season == s].dropna(subset=besoin)
        mc = ModeleComplet.entrainer(X[X.Season < s], s - 1)
        r = probas_bloc(mc, TE)
        cote = {"Victoire Domicile": TE.OddHome, "Match nul": TE.OddDraw, "Victoire Extérieur": TE.OddAway,
                "Plus de 2,5 buts": TE.Over25, "Moins de 2,5 buts": TE.Under25}
        for fam, nom, fp, fo in definitions():
            lignes.append(pd.DataFrame({"mid": TE.index, "saison": s, "famille": fam, "marché": nom, "p": fp(r), "réalisé": fo(TE).values,
                                        "cote": cote[nom].values if nom in cote else np.nan}))
    A = pd.concat(lignes, ignore_index=True)
    A["palier"] = [palier(p) for p in A.p]
    A["gain"] = np.where(A["réalisé"], A.cote - 1, -1.0)
    par_palier = A.groupby("palier").agg(décisions=("p", "size"), probabilité_annoncée=("p", "mean"), taux_réalisé=("réalisé", "mean"),
                                         paris_avec_cote=("cote", "count"), rendement_aux_cotes=("gain", lambda g: g[A.loc[g.index, "cote"].notna()].mean()))
    U = A[A.p < 0.95]
    prud = U.loc[U.groupby("mid").p.idxmax()]
    par_famille = A.groupby("famille").agg(décisions=("p", "size"), probabilité_annoncée=("p", "mean"), taux_réalisé=("réalisé", "mean"))
    prudente = pd.DataFrame({"valeur": {"matchs": len(prud), "probabilité moyenne annoncée": prud.p.mean(), "taux de réussite réel": prud["réalisé"].mean()}})
    prudente_marches = prud.groupby("marché").agg(fois=("p", "size"), prob=("p", "mean"), réussite=("réalisé", "mean")).sort_values("fois", ascending=False)
    return {"paliers": par_palier, "familles": par_famille, "decision_prudente": prudente, "prudente_par_marche": prudente_marches.head(10)}


def _figure_saison(te, y, R, ll, ok, lig, titre):
    fig, ax = plt.subplots(1, 3, figsize=(17, 4.6))
    jours = te.MatchDate.values
    for nom in ["Elo seul", "v3", "v4", "Cotes"]:
        s = pd.Series(ll[nom]).groupby(jours).agg(["sum", "size"]).cumsum()
        cum = (s["sum"] / s["size"])[s["size"] >= 100]
        ax[0].plot(cum.index, cum.values, lw=2, color=COUL[nom], ls="--" if nom == "Cotes" else "-", label=f"{nom} (final {cum.iloc[-1]:.3f})")
    ax[0].set_title(f"Log loss cumulée — {titre}", loc="left", fontsize=11); ax[0].legend(frameon=False, loc="lower right", fontsize=9); ax[0].tick_params(axis="x", rotation=30)
    for nom in ["v4", "Cotes"]:
        P = R[nom]["P"][ok]; p = P.ravel(); o = np.eye(3)[y[ok]].ravel()
        g = pd.DataFrame({"p": p, "o": o, "b": pd.qcut(p, 10, labels=False, duplicates="drop")}).groupby("b").mean()
        ax[1].plot(g.p, g.o, "-o", lw=2, ms=6, color=COUL[nom], mec="white", mew=1.5, label=nom, ls="--" if nom == "Cotes" else "-")
    ax[1].plot([0, .85], [0, .85], color="#b5b4ae", lw=1); ax[1].set_xlabel("probabilité annoncée"); ax[1].set_ylabel("fréquence observée")
    ax[1].set_title("Calibration (1, X et 2 confondus)", loc="left", fontsize=11); ax[1].legend(frameon=False)
    xx = np.arange(len(lig)); wd = .2; cols = ["Elo seul", "v3", "v4", "Cotes"]
    for i, nom in enumerate(cols):
        ax[2].bar(xx + (i - 1.5) * wd, lig[nom], wd * .9, color=COUL[nom], label=nom)
    ax[2].set_xticks(xx, lig.index, rotation=15); ax[2].set_ylim(lig[cols].values.min() - .02, lig[cols].values.max() + .01)
    ax[2].set_title("Log loss 1X2 par ligue (axe tronqué)", loc="left", fontsize=11); ax[2].legend(frameon=False, ncol=4, fontsize=8, loc="upper left")
    plt.tight_layout()
    return fig


def afficher(res):
    """Affiche les tableaux d'un résultat de labo (dans un notebook : display ; sinon print)."""
    try:
        from IPython.display import display
    except ImportError:
        display = print
    for k, v in res.items():
        if isinstance(v, pd.DataFrame) and not k.startswith("_"):
            print(f"\n■ {k}"); display(v.round(4))


def enregistrer(res, prefixe, dossier="results"):
    os.makedirs(f"{dossier}/tables", exist_ok=True); os.makedirs(f"{dossier}/figures", exist_ok=True)
    for k, v in res.items():
        if k == "_fig":
            v.savefig(f"{dossier}/figures/{prefixe}.png", dpi=130, bbox_inches="tight")
        elif isinstance(v, pd.DataFrame) and not k.startswith("_"):
            v.to_csv(f"{dossier}/tables/{prefixe}_{k}.csv")
