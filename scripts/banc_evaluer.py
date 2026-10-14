"""Évaluation scientifique du banc d'essai et entraînement du moteur de sélection (Phases 2 à 4).

Lit data/banc_oof.pkl (scripts/banc_generer.py) et produit :
  - results/tables/v6_*.csv : matrice d'expériences E0-E8, calibration, ablations, sélection ;
  - footpred/artefacts/selection.json : ensemble, méta-modèle et seuils utilisés en production ;
  - docs/resultats_v6.md : rapport généré (chiffres uniquement issus de ce script).

Fenêtres : A = 2016-2020 (premières années d'empilement), B = 2021-2024 (validation : ensemble par fenêtre glissante,
méta-modèle, seuils), T = 2025/26 (test final réservé : aucune décision n'y est prise).
"""
import json
import os
import pickle
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import confusion_matrix, f1_score, recall_score

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from footpred import evaluation as E                                      # noqa: E402
from footpred import selection as S                                       # noqa: E402
from footpred.banc import FENETRE_A, FENETRE_B, FENETRE_T                  # noqa: E402
from footpred.version import MODELE, __version__                          # noqa: E402

RACINE = os.path.join(os.path.dirname(__file__), "..")
TABLES = os.path.join(RACINE, "results", "tables")
ART = os.path.join(RACINE, "footpred", "artefacts")
CIBLE_RETENUE, CIBLE_PRUDENTE = 0.85, 0.75          # fiabilité minimale exigée sur la validation (choix produit, documenté)
BASE = ["E0 Goalgebra v5 (logit)", "E1 Logistique Elo + forme", "E2 Dixon-Coles (buts)", "E3 CatBoost (sport)"]
MARCHE = "E5 Marché seul (Shin)"
os.makedirs(TABLES, exist_ok=True); os.makedirs(ART, exist_ok=True)

B = pickle.load(open(os.path.join(RACINE, "data", "banc_oof.pkl"), "rb"))
meta, P, MDC = B["meta"], B["P"], B["M"].astype(float)
y, saison = meta.y.values.astype(int), meta.Season.values
h, a = meta.FTHome.values.astype(int), meta.FTAway.values.astype(int)
cotes = np.isfinite(P[MARCHE]).all(1)
for k in [k for k in P if k.startswith("ablation")]:            # ablations calculées sur B et T seulement : remise à la taille complète
    plein = np.full((len(y), 3), np.nan); plein[np.isin(saison, FENETRE_B + FENETRE_T)] = P[k]; P[k] = plein
RAPPORT = []


def section(t):
    RAPPORT.append(f"\n## {t}\n"); print("\n==", t)


def table(df: pd.DataFrame, nom: str, fmt="{:.4f}"):
    df.to_csv(os.path.join(TABLES, f"v6_{nom}.csv"))
    d = df.copy()
    for c in d.columns:
        if d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda v: "—" if pd.isna(v) else fmt.format(v))
    RAPPORT.append(d.to_markdown()); print(d.to_string())


def metriques(Pm, yy) -> dict:
    pred = Pm.argmax(1)
    rec = recall_score(yy, pred, labels=[0, 1, 2], average=None, zero_division=0)
    return {"n": len(yy), "log loss": E.log_loss(Pm, yy).mean(), "Brier": E.brier(Pm, yy).mean(), "RPS": E.rps(Pm, yy).mean(),
            "ECE": E.ece(Pm, yy), "accuracy": np.mean(pred == yy), "macro F1": f1_score(yy, pred, average="macro"),
            "rappel 1": rec[0], "rappel X": rec[1], "rappel 2": rec[2]}


# ================================================================ 1. ensembles par fenêtre glissante (aucune fuite)
section("1. Ensembles appris par fenêtre glissante")
ENS_SPORT = np.full((len(y), 3), np.nan); ENS_MARCHE = np.full((len(y), 3), np.nan)
CAL = {k: np.full((len(y), 3), np.nan) for k in ("E0 brut", "E0 température", "E0 multinomiale", "E0 isotonique")}
poids_ens = []
for t in FENETRE_B + FENETRE_T:
    tr, te = (saison >= FENETRE_A[0]) & (saison < t), saison == t
    es = S.Ensemble(BASE).fit({k: P[k][tr] for k in BASE}, y[tr])
    ENS_SPORT[te] = es.predict({k: P[k][te] for k in BASE})
    em = S.Ensemble(BASE + [MARCHE]).fit({k: P[k][tr] for k in BASE + [MARCHE]}, y[tr])
    ENS_MARCHE[te] = em.predict({k: P[k][te] for k in BASE + [MARCHE]})
    poids_ens.append({"saison test": t, **{f"{k} · log(P1/PX)": c for k, c in zip(BASE, np.round((es.lr.coef_[0] - es.lr.coef_[1])[::2], 3))}})
    # calibrations de E0 (comparaison des méthodes, apprises sur les saisons antérieures uniquement)
    p0 = P[BASE[0]]
    CAL["E0 brut"][te] = p0[te]
    lp = np.log(np.clip(p0, 1e-9, 1))
    Ts = np.linspace(0.6, 1.6, 101)
    T_opt = Ts[np.argmin([E.log_loss(np.exp(lp[tr] / T_) / np.exp(lp[tr] / T_).sum(1, keepdims=True), y[tr]).mean() for T_ in Ts])]
    q = np.exp(lp[te] / T_opt); CAL["E0 température"][te] = q / q.sum(1, keepdims=True)
    CAL["E0 multinomiale"][te] = S.Ensemble([BASE[0]]).fit({BASE[0]: p0[tr]}, y[tr]).predict({BASE[0]: p0[te]})
    iso = np.column_stack([IsotonicRegression(out_of_bounds="clip", y_min=1e-4, y_max=1).fit(p0[tr, k], y[tr] == k).predict(p0[te, k]) for k in range(3)])
    CAL["E0 isotonique"][te] = iso / iso.sum(1, keepdims=True)
table(pd.DataFrame(poids_ens).set_index("saison test"), "poids_ensemble", "{:.3f}")
RAPPORT.append("\nCoefficients de l'empilement (log P1/PX) par saison de test : leur stabilité indique si l'ensemble est robuste.")

# ================================================================ 2. matrice d'expériences (mêmes matchs)
section("2. Matrice d'expériences sur les mêmes matchs (cotes disponibles)")
MOD = {"E0 Goalgebra v5 (logit)": P[BASE[0]], "Elo seul": P["Elo seul"], "E1 Logistique Elo + forme": P[BASE[1]], "E2 Dixon-Coles (buts)": P[BASE[2]],
       "E3 CatBoost (sport)": P[BASE[3]], "E5 Marché seul (Shin)": P[MARCHE], "E6 Sport + marché (empilement)": ENS_MARCHE,
       "E7 Ensemble sport calibré": ENS_SPORT}
freq = np.zeros((len(y), 3))
for t in set(saison):
    tr = saison < t
    if tr.any():
        freq[saison == t] = np.bincount(y[tr], minlength=3) / tr.sum()
MOD = {"Classe majoritaire (fréquences)": freq, **MOD}
for nom_f, fen in (("validation B 2021-2024", FENETRE_B), ("test final T 2025-26", FENETRE_T)):
    m = np.isin(saison, fen) & cotes & np.all([np.isfinite(v).all(1) for v in MOD.values()], axis=0)
    RAPPORT.append(f"\n### {nom_f} — {m.sum()} matchs communs\n")
    table(pd.DataFrame({k: metriques(v[m], y[m]) for k, v in MOD.items()}).T, f"matrice_{fen[0]}")
    ll = {k: E.log_loss(v[m], y[m]) for k, v in MOD.items()}
    tests = []
    for a_, b_ in (("E7 Ensemble sport calibré", "E0 Goalgebra v5 (logit)"), ("E3 CatBoost (sport)", "E0 Goalgebra v5 (logit)"),
                   ("E2 Dixon-Coles (buts)", "E0 Goalgebra v5 (logit)"), ("E0 Goalgebra v5 (logit)", "Elo seul"),
                   ("E6 Sport + marché (empilement)", "E5 Marché seul (Shin)"), ("E7 Ensemble sport calibré", "E5 Marché seul (Shin)")):
        d = ll[a_] - ll[b_]; lo, hi = E.ic_bootstrap(d)
        tests.append({"comparaison": f"{a_} − {b_}", "Δ log loss ×1e3": 1e3 * d.mean(), "IC bas": 1e3 * lo, "IC haut": 1e3 * hi,
                      "significatif": "oui" if (hi < 0 or lo > 0) else "non"})
    table(pd.DataFrame(tests).set_index("comparaison"), f"tests_{fen[0]}", "{:.2f}")
    if fen == FENETRE_T:
        cm = confusion_matrix(y[m], MOD["E7 Ensemble sport calibré"][m].argmax(1), labels=[0, 1, 2])
        RAPPORT.append("\nMatrice de confusion E7 (lignes = réel 1/X/2, colonnes = prédit) :\n")
        table(pd.DataFrame(cm, index=["réel 1", "réel X", "réel 2"], columns=["prédit 1", "prédit X", "prédit 2"]), "confusion_T", "{:.0f}")

# stabilité par saison
section("3. Stabilité par saison (log loss, mêmes matchs)")
rows = []
for t in FENETRE_B + FENETRE_T:
    m = (saison == t) & cotes & np.isfinite(ENS_SPORT).all(1)
    rows.append({"saison": f"{t}/{(t + 1) % 100:02d}", **{k: E.log_loss(MOD[k][m], y[m]).mean() for k in
                 ["Elo seul", "E0 Goalgebra v5 (logit)", "E2 Dixon-Coles (buts)", "E3 CatBoost (sport)", "E7 Ensemble sport calibré", "E6 Sport + marché (empilement)", "E5 Marché seul (Shin)"]}})
table(pd.DataFrame(rows).set_index("saison"), "stabilite")

# ================================================================ 4. calibration
section("4. Méthodes de calibration de E0 (apprises sur les saisons antérieures)")
m = np.isin(saison, FENETRE_B + FENETRE_T)
table(pd.DataFrame({k: metriques(v[m], y[m]) for k, v in CAL.items()}).T[["n", "log loss", "Brier", "ECE"]], "calibration_methodes")


def pente_intercept(p, o):
    import statsmodels.api as sm
    r = sm.Logit(o, sm.add_constant(S.logit(p))).fit(disp=0)
    return r.params[1], r.params[0]


rows = []
for nom, Pm in (("E0", P[BASE[0]]), ("E7", ENS_SPORT)):
    for k, lab in enumerate("1X2"):
        mm = m & np.isfinite(Pm).all(1)
        pe, it = pente_intercept(Pm[mm, k], (y[mm] == k).astype(int))
        rows.append({"modèle": nom, "issue": lab, "pente": pe, "intercept": it})
table(pd.DataFrame(rows).set_index(["modèle", "issue"]), "calibration_pente", "{:.3f}")
RAPPORT.append("\nPente 1 et intercept 0 = calibration parfaite ; pente < 1 = probabilités trop extrêmes.")

# ================================================================ 5. ablations
section("5. Ablations du modèle v5 (Δ log loss ×1e3 par rapport au modèle complet ; > 0 = la famille retirée était utile)")
rows = []
for nom in [k for k in P if k.startswith("ablation")]:
    for nom_f, fen in (("B 2021-2024", FENETRE_B), ("T 2025-26", FENETRE_T)):
        mm = np.isin(saison, fen) & np.isfinite(P[nom]).all(1)
        d = E.log_loss(P[nom][mm], y[mm]) - E.log_loss(P[BASE[0]][mm], y[mm]); lo, hi = E.ic_bootstrap(d)
        rows.append({"variante": nom.replace("ablation · ", ""), "fenêtre": nom_f, "Δ ×1e3": 1e3 * d.mean(), "IC bas": 1e3 * lo, "IC haut": 1e3 * hi,
                     "significatif": "oui" if (hi < 0 or lo > 0) else "non"})
table(pd.DataFrame(rows).set_index(["variante", "fenêtre"]), "ablations", "{:.2f}")
RAPPORT.append("\nSans xG fournisseur (E4) : non réalisé, aucune source gratuite et fiable joignable ; la famille « forme / xG proxy » "
               "correspond au xG approché (tirs cadrés × conversion). Variables événementielles : étude séparée (resultats.md §13).")

# ================================================================ 6. moteur de sélection
section("6. Moteur de sélection : distribution conjointe cohérente, méta-modèle, seuils (validation B), test T")
# source des probabilités 1X2 : l'ensemble n'est retenu que s'il bat E0 sur la validation B (jamais sur T)
mB = np.isin(saison, FENETRE_B) & np.isfinite(ENS_SPORT).all(1)
ll_e0, ll_e7 = E.log_loss(P[BASE[0]][mB], y[mB]).mean(), E.log_loss(ENS_SPORT[mB], y[mB]).mean()
SOURCE = "E7 Ensemble sport calibré" if ll_e7 < ll_e0 else BASE[0]
PSRC = ENS_SPORT if SOURCE.startswith("E7") else P[BASE[0]]
RAPPORT.append(f"\nSource des probabilités 1X2 retenue sur la validation B : **{SOURCE}** (log loss B : E0 {ll_e0:.4f}, E7 {ll_e7:.4f}). "
               "Un ensemble qui n'améliore pas la validation n'est pas utilisé.")
CLES = list(S.MARCHES)
fam_de = {k: S.MARCHES[k][1] for k in CLES}
D_all = S.desaccord([P[k] for k in BASE])
H_all = S.entropie(PSRC)
install = (np.nan_to_num(meta.joues_h.values, nan=0) >= 5) & (np.nan_to_num(meta.joues_a.values, nan=0) >= 5)
pm_over = meta.over25_marche.values
# fréquences historiques des marchés (référence quand aucune cote n'existe) : fenêtre A uniquement
mA = np.isin(saison, FENETRE_A)
base_rate = {}
for k in CLES:
    o = np.array([S.issue(k, hh, aa) for hh, aa in zip(h[mA], a[mA])], dtype=object)
    o = np.array([v for v in o if v is not None], float); base_rate[k] = float(o.mean())


def candidats(idx, ens):
    """Lignes candidates (un marché par ligne) pour les matchs idx, à partir de l'ensemble `ens` (n, 3)."""
    Madj = S.ajuster_grille(MDC[idx], ens[idx])
    pk = S.probas_marches(Madj)
    disp = {}                                                     # dispersion des modèles de base, par marché (écart-type des logits)
    par_mod = [S.probas_marches(S.ajuster_grille(MDC[idx], P[k][idx])) for k in BASE]
    for k in CLES:
        disp[k] = np.std(np.column_stack([S.logit(pm_[k]) for pm_ in par_mod]), axis=1)
    lignes = []
    for j, i in enumerate(idx):
        ref = S.probas_marche_reference(P[MARCHE][i] if cotes[i] else None, pm_over[i])
        for k in CLES:
            o = S.issue(k, h[i], a[i])
            lignes.append({"i": i, "cle": k, "famille": fam_de[k], "p": pk[k][j], "disp": disp[k][j], "ref": ref.get(k, base_rate[k]),
                           "ref_marche": k in ref, "D": D_all[i], "H": H_all[i], "installee": install[i], "cotes": cotes[i], "issue": o})
    return pd.DataFrame(lignes)


iB = np.where(np.isin(saison, FENETRE_B) & np.isfinite(ENS_SPORT).all(1))[0]
iT = np.where(np.isin(saison, FENETRE_T) & np.isfinite(ENS_SPORT).all(1))[0]
CB, CT = candidats(iB, PSRC), candidats(iT, PSRC)
CB["saison"], CT["saison"] = saison[CB.i], saison[CT.i]
Z = lambda df: S.variables_meta(df.p.values, df.famille.values, df.D.values, df.H.values, df.installee.values, df.cotes.values)

# méta-modèle hors échantillon sur B (une saison prédite par un méta-modèle appris sur les autres saisons de B) → seuils
CB["p_meta"], CB["p_bas"] = np.nan, np.nan
for t in FENETRE_B:
    tr, te = (CB.saison != t) & CB.issue.notna(), CB.saison == t
    mm = S.MetaModele().fit(Z(CB[tr]), CB.issue[tr].astype(int).values)
    pp, pb = mm.predict(Z(CB[te]), CB.disp[te].values)
    CB.loc[te, "p_meta"], CB.loc[te, "p_bas"] = pp, pb
CB["info"] = S.kl_bits(CB.p_meta, CB.ref)
meta_final = S.MetaModele().fit(Z(CB[CB.issue.notna()]), CB.issue[CB.issue.notna()].astype(int).values)
pp, pb = meta_final.predict(Z(CT), CT.disp.values)
CT["p_meta"], CT["p_bas"], CT["info"] = pp, pb, S.kl_bits(pp, CT.ref.values)
pickle.dump({"CB": CB, "CT": CT, "meta": meta, "SOURCE": SOURCE}, open(os.path.join(RACINE, "data", "banc_candidats.pkl"), "wb"))
table(pd.DataFrame({"coefficient": meta_final.beta, "erreur type": np.sqrt(np.diag(meta_final.cov))}, index=S.NOMS_META), "meta_modele", "{:.3f}")


def appliquer(C_, seuils, mode="compromis"):
    """Version vectorisée de selection.decider (même logique ; vérifiée par tests/test_selection.py) pour tous les matchs."""
    C2 = C_.drop(columns="p").assign(lift=lambda x: x.p_meta - x.ref)
    C2 = C2.sort_values("p_meta" if mode == "probable" else "lift", ascending=False, kind="stable")
    inf = C2[C2["info"] >= seuils["info_min"]]
    ret = inf[(inf.p_bas >= seuils["p_bas_min"]) & (inf.p_bas > inf.ref) & (inf.D <= seuils["desaccord_max"])].drop_duplicates("i").assign(decision="retenue")
    reste = inf[~inf.i.isin(ret.i)]
    pru = reste[(reste.p_meta >= seuils["p_prudente_min"]) & (reste.p_meta > reste.ref)].drop_duplicates("i").assign(decision="prudente")
    abst = pd.DataFrame({"i": C2.i[~C2.i.isin(ret.i) & ~C2.i.isin(pru.i)].unique()}).assign(decision="abstention")
    # pour mesurer ce que l'abstention écarte : sélection la plus probable du match (jamais publiée)
    abst = abst.merge(C2.sort_values("p_meta", ascending=False).drop_duplicates("i")[["i", "cle", "p_meta", "p_bas", "info", "issue", "famille", "ref"]], on="i", how="left")
    R = pd.concat([ret, pru, abst], ignore_index=True)
    return R.rename(columns={"p_meta": "p"})[["i", "decision", "cle", "p", "p_bas", "info", "issue", "famille", "ref"]]


def bilan(R, n_total):
    ok = R[R.issue.notna()]
    return {"matchs": len(R), "couverture": len(R) / n_total, "réussite": ok.issue.astype(float).mean() if len(ok) else np.nan,
            "p moyenne annoncée": ok.p.mean() if len(ok) else np.nan,
            "référence moyenne": ok.ref.mean() if len(ok) and "ref" in ok else np.nan,
            "succès en plus de la référence": (ok.issue.astype(float) - ok.ref).mean() if len(ok) and "ref" in ok else np.nan, "borne basse moyenne": ok.p_bas.mean() if len(ok) else np.nan,
            "log loss": E.log_loss_binaire(ok.p.values, ok.issue.astype(int).values).mean() if len(ok) else np.nan,
            "Brier": float(np.mean((ok.p.values - ok.issue.astype(float).values) ** 2)) if len(ok) else np.nan,
            "information publiée (bits)": float(R["info"].where(R.decision != "abstention", 0).sum()) if "decision" in R else float(R["info"].sum())}


# recherche des seuils sur B uniquement (sélection sélective, courbe risque-couverture) : couverture maximale sous contraintes —
# réussite des retenues ≥ CIBLE_RETENUE dans CHAQUE saison de B, écart de calibration ≥ −2 points ; à couverture égale,
# le plus grand nombre de succès en plus de la référence.
grille_pb = np.round(np.arange(0.60, 0.931, 0.01), 2)
grille_info = [0.0, 0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.08]
grille_D = [float(np.quantile(D_all[iB], q)) for q in (0.8, 0.9, 0.95)] + [1.0]
meilleur, essais = None, []
CBo = CB.copy()
for dmax in grille_D:
    for imin in grille_info:
        for pbm in grille_pb:
            s_ = {"p_bas_min": float(pbm), "info_min": imin, "desaccord_max": dmax, "p_prudente_min": 1.01}
            R = appliquer(CBo, s_)
            Rr = R[R.decision == "retenue"]; ok = Rr[Rr.issue.notna()].assign(saison=lambda x: saison[x.i.values])
            if len(ok) < 200:
                continue
            hit_s = ok.groupby("saison").issue.apply(lambda v: v.astype(float).mean())
            gain = float((ok.issue.astype(float) - ok.ref).sum())
            essais.append({"desaccord_max": dmax, "info_min": imin, "p_bas_min": pbm, "retenues": len(Rr), "couverture": len(Rr) / CB.i.nunique(),
                           "réussite": ok.issue.astype(float).mean(), "réussite min. par saison": hit_s.min(), "p moyenne": ok.p.mean(), "succès en plus": gain})
            cle = (len(Rr), gain)
            if hit_s.min() >= CIBLE_RETENUE and ok.issue.astype(float).mean() - ok.p.mean() >= -0.02 and (meilleur is None or cle > meilleur[1]):
                meilleur = (s_, cle)
    print("désaccord max", round(dmax, 3), "testé", flush=True)
pd.DataFrame(essais).to_csv(os.path.join(TABLES, "v6_grille_seuils.csv"), index=False)
seuils = meilleur[0]
# seuil prudent : le plus bas qui garde une réussite ≥ CIBLE_PRUDENTE dans chaque saison de B
for tp in np.round(np.arange(0.50, 0.95, 0.01), 2):
    R = appliquer(CBo, {**seuils, "p_prudente_min": float(tp)})
    ok = R[(R.decision == "prudente") & R.issue.notna()].assign(saison=lambda x: saison[x.i.values])
    if len(ok) >= 100 and ok.groupby("saison").issue.apply(lambda v: v.astype(float).mean()).min() >= CIBLE_PRUDENTE:
        seuils["p_prudente_min"] = float(tp); break
seuils = {k: float(v) for k, v in seuils.items()}
RAPPORT.append(f"\nSeuils choisis sur la validation B (cibles : retenues ≥ {CIBLE_RETENUE:.0%}, prudentes ≥ {CIBLE_PRUDENTE:.0%}, "
               f"dans chaque saison, écart de calibration ≥ −2 points ; objectif : couverture maximale) : `{json.dumps(seuils)}`")
print("seuils :", seuils)

# évaluation : B (hors échantillon pour le méta-modèle, mais seuils choisis dessus) et T (test réservé)
for nom_f, C_ in (("validation B", CB), ("test final T 2025-26", CT)):
    for mode in ("compromis", "probable"):
        R = appliquer(C_, seuils, mode)
        n = len(R)
        rows = {d: bilan(R[R.decision == d], n) for d in ("retenue", "prudente", "abstention")}
        # référence : issue 1X2 la plus probable pour tous les matchs
        g = C_[C_.cle.isin(["home", "draw", "away"])].sort_values("p_meta").groupby("i").tail(1)
        rows["tous les matchs (1X2 le plus probable)"] = bilan(g.drop(columns="p").rename(columns={"p_meta": "p"}), n)
        RAPPORT.append(f"\n### {nom_f} — mode « {mode} »\n")
        table(pd.DataFrame(rows).T, f"selection_{'B' if 'B' in nom_f else 'T'}_{mode}")
        if mode == "compromis" and "T" in nom_f:
            Rt = R
RAPPORT.append("\nRéussite des abstentions = réussite qu'aurait eue la sélection la plus informative si on l'avait retenue (pour vérifier "
               "que l'abstention écarte bien des cas moins fiables).")
# détail test par famille et par ligue (sélections retenues)
section("7. Test final : sélections retenues par famille de marché et par championnat")
Rt["ligue"] = meta.Division.values[Rt.i.values]
ret = Rt[(Rt.decision == "retenue") & Rt.issue.notna()]
table(ret.groupby("famille").agg(sélections=("issue", "size"), réussite=("issue", lambda s: s.astype(float).mean()), p_moyenne=("p", "mean")), "selection_T_familles")
table(ret.groupby("ligue").agg(sélections=("issue", "size"), réussite=("issue", lambda s: s.astype(float).mean()), p_moyenne=("p", "mean")), "selection_T_ligues")
# calibration du méta-modèle sur T (toutes les lignes candidates)
ok = CT[CT.issue.notna()]
bins = pd.cut(ok.p_meta, np.arange(0, 1.0001, 0.1))
table(ok.groupby(bins, observed=True).agg(n=("issue", "size"), annoncé=("p_meta", "mean"), observé=("issue", lambda s: s.astype(float).mean())), "calibration_meta_T", "{:.3f}")

# valeur (secondaire) : sélections retenues avec une cote réellement cotée (1X2 moyenne du marché, plus/moins 2,5)
section("8. Valeur statistique (secondaire, cotes moyennes du marché, pas de cotes de clôture)")
cote_de = {"home": "OddHome", "draw": "OddDraw", "away": "OddAway"}
rows = []
for _, r in ret.iterrows():
    c = meta[cote_de[r.cle]].values[r.i] if r.cle in cote_de else (meta.Over25.values[r.i] if r.cle == "over25" else (meta.Under25.values[r.i] if r.cle == "under25" else np.nan))
    if np.isfinite(c) and c > 1:
        rows.append({"gain": (c - 1) if r.issue == 1 else -1.0, "EV": r.p * c - 1, "EV prudente": r.p_bas * c - 1})
V = pd.DataFrame(rows)
if len(V):
    lo, hi = E.ic_bootstrap(V.gain.values)
    table(pd.DataFrame({"sélections avec cote": [len(V)], "rendement moyen": [V.gain.mean()], "IC bas": [lo], "IC haut": [hi],
                        "EV annoncée moyenne": [V.EV.mean()], "part EV prudente > 0": [(V["EV prudente"] > 0).mean()]}, index=["test T"]), "valeur_T", "{:.3f}")
RAPPORT.append("\nLe rendement n'est pas un objectif : les cotes moyennes incluent la marge du bookmaker, et aucune cote de clôture n'est disponible.")

# fiabilité historique (validation B, sélections retenues) par famille de marché : affichée sur chaque fiche
RB = appliquer(CB, seuils)
okB = RB[(RB.decision == "retenue") & RB.issue.notna()]
fam_B = {f: {"n": int(len(g)), "reussite": float(g.issue.astype(float).mean()), "annonce": float(g.p.mean())} for f, g in okB.groupby("famille")}
RT = appliquer(CT, seuils); n_T = RT.i.nunique()
resume_T = {d: {"n": int((RT.decision == d).sum()), "couverture": float((RT.decision == d).mean()),
                "reussite": float(RT[(RT.decision == d) & RT.issue.notna()].issue.astype(float).mean()) if ((RT.decision == d) & RT.issue.notna()).any() else None,
                "annonce": float(RT[RT.decision == d].p.mean()) if (RT.decision == d).any() else None} for d in ("retenue", "prudente", "abstention")}

# ================================================================ 9. artefact de production
ens_prod = S.Ensemble(BASE).fit({k: P[k][np.isin(saison, FENETRE_A + FENETRE_B)] for k in BASE}, y[np.isin(saison, FENETRE_A + FENETRE_B)])
ens_prod_m = S.Ensemble(BASE + [MARCHE]).fit({k: P[k][np.isin(saison, FENETRE_A + FENETRE_B)] for k in BASE + [MARCHE]}, y[np.isin(saison, FENETRE_A + FENETRE_B)])
art = {"source_1x2": "ensemble" if SOURCE.startswith("E7") else "E0", "version": MODELE, "package": __version__, "cree_le": datetime.now(timezone.utc).isoformat(),
       "fenetres": {"A": FENETRE_A, "B": FENETRE_B, "T": FENETRE_T}, "modeles_base": BASE,
       "ensemble_sport": ens_prod.etat(), "ensemble_marche": ens_prod_m.etat(), "meta": meta_final.etat(), "seuils": seuils,
       "frequences_marches": base_rate, "cibles": {"retenue": CIBLE_RETENUE, "prudente": CIBLE_PRUDENTE},
       "fiabilite_familles_B": fam_B, "test_T": {"saison": "2025/26", "matchs": int(n_T), **resume_T}}
json.dump(art, open(os.path.join(ART, "selection.json"), "w"), indent=1)

with open(os.path.join(RACINE, "docs", "resultats_v6.md"), "w", encoding="utf-8") as f:
    f.write(f"# Résultats du banc d'essai v6 (généré par `scripts/banc_evaluer.py`, {datetime.now(timezone.utc):%Y-%m-%d})\n\n"
            "Prédictions hors échantillon strictement chronologiques (`footpred/banc.py`). Fenêtre A = 2016-2020, "
            "B = 2021-2024 (validation : empilement par fenêtre glissante, méta-modèle, seuils), T = 2025/26 (test final réservé, "
            "aucune décision n'y est prise). Les variables de v5 ont été étudiées sur 2010-2025 : T n'est donc pas totalement vierge "
            "pour E0 ; l'évaluation prospective est le journal 2026/27.\n" + "\n".join(RAPPORT) + "\n")
print("\nartefact :", os.path.join(ART, "selection.json"))
