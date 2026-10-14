"""Suivi en direct : journal horodaté des prédictions (écrit AVANT les matchs), puis évaluation une fois les résultats connus."""
import os
import datetime as dt
import numpy as np
import pandas as pd
from .data import charger_matchs
from .evaluation import log_loss, log_loss_binaire, rps, ic_bootstrap, proba_cotes

COLONNES = ["horodatage", "donnees_au", "version", "date_match", "dom", "ext", "P1", "PX", "P2",
            "buts_dom", "buts_ext", "P_over25", "P_btts", "fiabilite", "pronostic"]


def predire_journee(predicteur, matchs, chemin="journal/journal_predictions.csv", version="v4"):
    """matchs = [("Équipe dom", "Équipe ext"[, "AAAA-MM-JJ"]), ...]. Ajoute les prédictions au journal et les renvoie."""
    lignes = []
    for m in matchs:
        dom, ext = m[0], m[1]
        try:
            r = predicteur.simulation(dom, ext, afficher=False)
        except ValueError as e:
            print("  ✗", e); continue
        lignes.append({"horodatage": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "donnees_au": str(predicteur.d.date_max.date()),
                       "version": version, "date_match": m[2] if len(m) > 2 else "", "dom": dom, "ext": ext,
                       "P1": round(r["1"], 4), "PX": round(r["X"], 4), "P2": round(r["2"], 4),
                       "buts_dom": round(r["buts_dom"], 3), "buts_ext": round(r["buts_ext"], 3),
                       "P_over25": round(r["over25"], 4), "P_btts": round(r["btts"], 4), "fiabilite": r["fiabilite"],
                       "pronostic": ["1", "X", "2"][int(np.argmax([r["1"], r["X"], r["2"]]))]})
    new = pd.DataFrame(lignes, columns=COLONNES)
    if new.empty:
        return new
    os.makedirs(os.path.dirname(chemin) or ".", exist_ok=True)
    old = pd.read_csv(chemin) if os.path.exists(chemin) else pd.DataFrame(columns=COLONNES)
    pd.concat([old, new], ignore_index=True).to_csv(chemin, index=False)
    retard = (dt.date.today() - predicteur.d.date_max.date()).days
    print(f"{len(new)} prédictions ajoutées à {chemin} (données au {predicteur.d.date_max.date()})"
          + (f"  ⚠ données vieilles de {retard} jours" if retard > 7 else ""))
    return new


def evaluer_journal(chemin="journal/journal_predictions.csv", source=None, sortie="journal/journal_evalue.csv"):
    """Associe chaque prédiction au match joué APRÈS elle et calcule les scores (modèle et cotes)."""
    if not os.path.exists(chemin):
        print("Journal vide."); return None
    J = pd.read_csv(chemin, parse_dates=["horodatage"])
    res = charger_matchs(source, cache=None).dropna(subset=["FTResult"])
    lignes = []
    for i, j in J.iterrows():
        c = res[(res.HomeTeam == j.dom) & (res.AwayTeam == j.ext) & (res.MatchDate >= j.horodatage.normalize())]
        if isinstance(j.date_match, str) and j.date_match:
            c = c[(c.MatchDate - pd.Timestamp(j.date_match)).abs() <= pd.Timedelta(days=3)]
        if len(c):
            lignes.append((i, c.sort_values("MatchDate").iloc[0]))
    if not lignes:
        print(f"Aucun match du journal n'est encore joué ({len(J)} prédictions en attente)."); return None
    E = J.loc[[i for i, _ in lignes]].copy()
    R = pd.DataFrame([r for _, r in lignes], index=E.index)
    E = E.join(R[["MatchDate", "FTHome", "FTAway", "FTResult", "OddHome", "OddDraw", "OddAway"]])
    y = E.FTResult.map({"H": 0, "D": 1, "A": 2}).values; P = E[["P1", "PX", "P2"]].values
    Pm = proba_cotes(E); ok = ~np.isnan(Pm).any(1)
    E["LL_modele"] = log_loss(P, y); E["LL_cotes"] = np.where(ok, log_loss(np.nan_to_num(Pm, nan=1 / 3), y), np.nan)
    E["juste"] = P.argmax(1) == y
    E["LL_over25"] = log_loss_binaire(E.P_over25.values, (E.FTHome + E.FTAway > 2.5).values)
    print(f"ÉVALUATION : {len(E)} matchs joués / {len(J)} prédictions")
    print(f"  log loss 1X2 : modèle {E.LL_modele.mean():.4f} · cotes {E.LL_cotes.mean():.4f} · sans modèle ≈ 1,07")
    print(f"  RPS : modèle {rps(P, y).mean():.4f}   ·   pronostics justes {E.juste.mean():.1%}   ·   log loss over 2,5 {E.LL_over25.mean():.4f}")
    if ok.sum() >= 30:
        lo, hi = ic_bootstrap((E.LL_modele - E.LL_cotes).values[ok])
        print(f"  écart modèle − cotes : IC 95 % [{1000 * lo:+.1f} ; {1000 * hi:+.1f}] ×10⁻³")
    else:
        print("  (moins de 30 matchs : écarts pas encore interprétables)")
    if sortie:
        os.makedirs(os.path.dirname(sortie) or ".", exist_ok=True); E.to_csv(sortie, index=False)
    return E
