"""Aide à la décision statistique : tous les marchés d'un match classés du moins risqué au plus risqué.

« Risque » = probabilité que l'issue NE se réalise PAS, selon le modèle. Une issue peu risquée n'est pas pour autant
une bonne affaire : si des cotes sont fournies, on calcule aussi la valeur attendue (espérance de gain pour une mise de 1),
qui est le seul critère qui tient compte du prix. Sur 2021-2026, aucune règle de sélection n'a eu une espérance positive
démontrée (voir docs/resultats.md §5) : ces tableaux sont des outils d'analyse, pas des conseils de pari.
"""
import numpy as np
import pandas as pd

# Paliers de risque (probabilité de réussite selon le modèle)
PALIERS = [(0.80, "1 · très faible"), (0.65, "2 · faible"), (0.50, "3 · modéré"), (0.35, "4 · élevé"), (0.0, "5 · très élevé")]


def palier(p: float) -> str:
    for seuil, nom in PALIERS:
        if p >= seuil:
            return nom
    return PALIERS[-1][1]


def _g(r, *cles):
    v = r
    for c in cles:
        v = v[c]
    return v


def definitions(dom="Domicile", ext="Extérieur"):
    """(famille, marché, fonction probabilité(r), fonction résultat(match joué)). Fonctionne en scalaire comme en vectoriel."""
    M = [
        ("Résultat", f"Victoire {dom}", lambda r: r["1"], lambda m: m.FTHome > m.FTAway),
        ("Résultat", "Match nul", lambda r: r["X"], lambda m: m.FTHome == m.FTAway),
        ("Résultat", f"Victoire {ext}", lambda r: r["2"], lambda m: m.FTHome < m.FTAway),
        ("Double chance", f"{dom} ou nul (1X)", lambda r: r["1"] + r["X"], lambda m: m.FTHome >= m.FTAway),
        ("Double chance", f"Nul ou {ext} (X2)", lambda r: r["X"] + r["2"], lambda m: m.FTHome <= m.FTAway),
        ("Double chance", f"{dom} ou {ext} (12)", lambda r: r["1"] + r["2"], lambda m: m.FTHome != m.FTAway),
    ]
    for s, k in ((1.5, "over15"), (2.5, "over25"), (3.5, "over35")):
        M += [("Buts", f"Plus de {s:g} buts".replace(".", ","), lambda r, k=k: r[k], lambda m, s=s: m.FTHome + m.FTAway > s),
              ("Buts", f"Moins de {s:g} buts".replace(".", ","), lambda r, k=k: 1 - r[k], lambda m, s=s: m.FTHome + m.FTAway < s)]
    M += [("Buts", "Les deux équipes marquent", lambda r: r["btts"], lambda m: (m.FTHome > 0) & (m.FTAway > 0)),
          ("Buts", "Au moins une équipe ne marque pas", lambda r: 1 - r["btts"], lambda m: (m.FTHome == 0) | (m.FTAway == 0)),
          ("Buts", f"{dom} marque", lambda r: 1 - r["cs_ext"], lambda m: m.FTHome > 0),
          ("Buts", f"{ext} marque", lambda r: 1 - r["cs_dom"], lambda m: m.FTAway > 0)]
    for s in (8.5, 9.5, 10.5):
        M += [("Corners", f"Plus de {s:g} corners".replace(".", ","), lambda r, s=s: _g(r, "corners", "plus_de", s), lambda m, s=s: m.HomeCorners + m.AwayCorners > s),
              ("Corners", f"Moins de {s:g} corners".replace(".", ","), lambda r, s=s: 1 - _g(r, "corners", "plus_de", s), lambda m, s=s: m.HomeCorners + m.AwayCorners < s)]
    M += [("Corners", f"{dom} plus de 4,5 corners", lambda r: _g(r, "corners", "dom_plus_de", 4.5), lambda m: m.HomeCorners > 4.5),
          ("Corners", f"{ext} plus de 4,5 corners", lambda r: _g(r, "corners", "ext_plus_de", 4.5), lambda m: m.AwayCorners > 4.5)]
    for s in (3.5, 4.5):
        M += [("Cartons", f"Plus de {s:g} cartons jaunes".replace(".", ","), lambda r, s=s: _g(r, "jaunes", "plus_de", s), lambda m, s=s: m.HomeYellow + m.AwayYellow > s),
              ("Cartons", f"Moins de {s:g} cartons jaunes".replace(".", ","), lambda r, s=s: 1 - _g(r, "jaunes", "plus_de", s), lambda m, s=s: m.HomeYellow + m.AwayYellow < s)]
    M += [("Cartons", "Au moins un carton rouge", lambda r: _g(r, "rouges", "au_moins_un"), lambda m: m.HomeRed + m.AwayRed > 0),
          ("Cartons", "Aucun carton rouge", lambda r: 1 - _g(r, "rouges", "au_moins_un"), lambda m: m.HomeRed + m.AwayRed == 0)]
    return M


def classement(r: dict, cotes: dict | None = None) -> pd.DataFrame:
    """Tous les marchés du match, du moins risqué au plus risqué. `cotes` = {nom du marché: cote décimale} (facultatif)."""
    dom, ext = r["dom"], r["ext"]
    lignes = []
    for fam, nom, fp, _ in definitions(dom, ext):
        try:
            p = float(fp(r))
        except (KeyError, TypeError):
            continue
        lignes.append({"famille": fam, "marché": nom, "probabilité": p, "risque": palier(p), "cote juste": 1 / p if p > 0 else np.inf})
    T = pd.DataFrame(lignes)
    T["cote bookmaker"] = T["marché"].map(cotes or {}).astype(float)
    T["prob. implicite"] = 1 / T["cote bookmaker"]
    T["écart (pts)"] = 100 * (T["probabilité"] - T["prob. implicite"])
    T["valeur attendue"] = T["probabilité"] * T["cote bookmaker"] - 1
    return T.sort_values("probabilité", ascending=False).reset_index(drop=True)


def trois_decisions(T: pd.DataFrame, familles=None) -> pd.DataFrame:
    """Décision prudente (la plus probable), équilibrée (≈ 60 %) et audacieuse (≈ 40 %), parmi des marchés non triviaux."""
    U = T if familles is None else T[T.famille.isin(familles)]
    U = U[U["probabilité"] < 0.95]
    out = []
    for nom, cible in (("prudente", None), ("équilibrée", 0.60), ("audacieuse", 0.40)):
        i = U["probabilité"].idxmax() if cible is None else (U["probabilité"] - cible).abs().idxmin()
        out.append({"profil": nom, **U.loc[i].to_dict()})
    return pd.DataFrame(out)
