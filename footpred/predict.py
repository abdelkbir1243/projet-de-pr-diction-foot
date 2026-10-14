"""Prédiction d'un match à venir : probabilités 1X2, buts attendus, marchés dérivés, fiabilité."""
import numpy as np
import pandas as pd
from . import config as C
from .features import Donnees
from .models import ModeleComplet, grille
from .markets import marches, scores_probables, cote_juste, shin

# Précision observée de l'issue favorite selon la confiance du modèle (test walk-forward 2021-2026, v4).
# Recalculée par Predicteur.calibrer_fiabilite() si l'on fournit des prédictions de validation.
CONF_BINS = [0, .42, .50, .61, 1]
CONF_ACC = [0.39, 0.46, 0.54, 0.71]
NIVEAUX = ["faible", "moyenne", "bonne", "élevée"]
CONTEXTE_COLS = [f"{k}_{s}" for s in "ha" for k in ("repos", "charge", "joues", "rang", "titre", "europe", "maintien", "sansenjeu",
                                                    "promu", "premiere", "champion")]


class Predicteur:
    def __init__(self, donnees: Donnees, modele: ModeleComplet | None = None):
        self.d = donnees
        self.modele = modele or ModeleComplet.entrainer(donnees.X)
        self.conf_acc = list(CONF_ACC)

    def calibrer_fiabilite(self, P: np.ndarray, y: np.ndarray):
        s = pd.DataFrame({"pmax": P.max(1), "ok": P.argmax(1) == y})
        self.conf_acc = s.groupby(pd.cut(s.pmax, CONF_BINS), observed=False).ok.mean().fillna(0).tolist()

    # ------------------------------------------------------------------ calcul
    def predire(self, dom: str, ext: str, elo_dom=None, elo_ext=None, cotes=None, jour=None, lg=None) -> dict:
        v, a, b = self.d.variables_match(dom, ext, elo_dom, elo_ext, jour, lg)
        r = self._calculer(pd.DataFrame([v]), dom, ext, a["lg"], fin=min(a["restants"], b["restants"]) <= 5)
        r.update({"donnees_au": max(a["date"], b["date"]), "contexte": a["contexte"], "_a": a, "_b": b})
        if cotes is not None:
            pm, marge = shin(cotes)
            r["marche"] = {"1": pm[0], "X": pm[1], "2": pm[2], "marge": marge}
        return r

    def predire_ligne(self, ligne: pd.Series) -> dict:
        """Prédiction à partir des variables d'avant-match d'un match historique (ligne de Donnees.X).
        Utilisée avec un modèle entraîné sur les saisons précédentes : prédiction hors échantillon d'un match déjà joué."""
        cols = [c for c in ligne.index if c in set(self.modele.m1x2.cols) | set(self.modele.buts.cols) | set(C.FE_CORNERS + C.FE_JAUNES + C.FE_ROUGES)]
        x = pd.DataFrame([ligne[cols].astype(float)])
        r = self._calculer(x, ligne.HomeTeam, ligne.AwayTeam, ligne.Division, fin=False)
        r["contexte"] = {k: (float(ligne[k]) if k in ligne and pd.notna(ligne[k]) else None) for k in CONTEXTE_COLS}
        return r

    def _calculer(self, x: pd.DataFrame, dom: str, ext: str, lg: str, fin: bool) -> dict:
        p = self.modele.m1x2.predict(x)[0]
        lh, la = (float(z[0]) for z in self.modele.buts.lambdas(x))
        M = grille(lh, la, self.modele.buts.rho)
        mk = marches(M, self.modele.buts.k_ht, lh, la)
        k = int(np.digitize(p.max(), CONF_BINS[1:-1]))
        r = {"dom": dom, "ext": ext, "ligue": C.LIGUES.get(lg, lg), "1": p[0], "X": p[1], "2": p[2],
             "buts_dom": lh, "buts_ext": la, **{k_: mk[k_] for k_ in ["over15", "over25", "over35", "btts", "cs_dom", "cs_ext", "but_1re_MT"]},
             "scores": scores_probables(M), "fiabilite": NIVEAUX[k], "precision_historique": self.conf_acc[k], "fin_de_saison": fin,
             "variables": {k_: float(x[k_].iloc[0]) for k_ in self.modele.m1x2.cols}, "_M": M}
        if self.modele.stats is not None:
            r.update(self.modele.stats.predire(x))
        return r

    # ------------------------------------------------------------------ affichage
    def simulation(self, dom, ext, elo_dom=None, elo_ext=None, cotes=None, n_sim=100_000, seed=0, afficher=True) -> dict:
        r = self.predire(dom, ext, elo_dom, elo_ext, cotes)
        M = r.pop("_M"); a = r.pop("_a"); b = r.pop("_b")
        idx = np.random.default_rng(seed).choice(M.size, n_sim, p=M.ravel()); sx, sy = np.divmod(idx, M.shape[1])
        r["monte_carlo"] = {"1": np.mean(sx > sy), "X": np.mean(sx == sy), "2": np.mean(sx < sy)}
        if not afficher:
            return r
        v = r["variables"]
        print("=" * 80); print(f"SIMULATION MATHÉMATIQUE v4 : {dom} – {ext}   ({r['ligue']})"); print("=" * 80)
        print(f"ΔElo {v['dElo']:+.2f} · ΔQ {v['dQ']:+.2f} · pi {v['pi_diff']:+.2f} · GAS : buts « bruts » "
              f"{np.exp(v['g_lh']):.2f} – {np.exp(v['g_la']):.2f} · données au {r['donnees_au']}")
        print(f"\n  ► Victoire {dom:<22s} {r['1']:6.1%}\n  ► Match nul {'':21s} {r['X']:6.1%}\n  ► Victoire {ext:<22s} {r['2']:6.1%}")
        print(f"\n  Buts attendus : {dom} {r['buts_dom']:.2f} · {ext} {r['buts_ext']:.2f}   ·   Monte-Carlo ({n_sim:,}) : "
              + " · ".join(f"{k} {q:.1%}" for k, q in r["monte_carlo"].items()))
        lignes = [("Victoire " + dom, r["1"]), ("Match nul", r["X"]), ("Victoire " + ext, r["2"]),
                  ("Plus de 1,5 but", r["over15"]), ("Plus de 2,5 buts", r["over25"]), ("Plus de 3,5 buts", r["over35"]),
                  ("Les deux équipes marquent", r["btts"]), ("But en 1re mi-temps", r["but_1re_MT"]),
                  (f"Cage inviolée {dom}", r["cs_dom"]), (f"Cage inviolée {ext}", r["cs_ext"])]
        print("\n  Marché                              Probabilité   Cote juste (1/p)")
        for nm, q in lignes:
            print(f"  {nm:35s} {q:8.1%}      {cote_juste(q):6.2f}")
        print("  Scores les plus probables : " + " · ".join(f"{s} {q:.1%}" for q, s in r["scores"]))
        if "corners" in r:
            c, j, rg = r["corners"], r["jaunes"], r["rouges"]
            print(f"\n  Corners attendus : {dom} {c['dom']:.1f} · {ext} {c['ext']:.1f} · total {c['total']:.1f}")
            print("    " + " · ".join(f"+{s:g} : {q:.0%}" for s, q in c["plus_de"].items()))
            print(f"  Cartons jaunes attendus : {dom} {j['dom']:.1f} · {ext} {j['ext']:.1f} · total {j['total']:.1f}")
            print("    " + " · ".join(f"+{s:g} : {q:.0%}" for s, q in j["plus_de"].items()))
            print(f"  Au moins un carton rouge : {rg['au_moins_un']:.0%} (cote juste {cote_juste(rg['au_moins_un']):.2f})")
        print(f"\n  Fiabilité : {r['fiabilite']} — à ce niveau de confiance, l'issue favorite s'est réalisée "
              f"{r['precision_historique']:.0%} du temps (test 2021-2026)")
        if r["fin_de_saison"]:
            print("  ⚠ Fin de saison : matchs historiquement moins prévisibles.")
        if "marche" in r:
            m = r["marche"]
            print(f"\n  Cotes {tuple(cotes)} — marge {m['marge']:.1%}, probabilités de Shin :")
            for k in ["1", "X", "2"]:
                print(f"    {k} : modèle {r[k]:.1%} · marché {m[k]:.1%} · écart {100 * (r[k] - m[k]):+.1f} pts")
            print("    Le marché est en moyenne plus précis que le modèle (log loss 0,972 contre 0,981) : un écart signale d'abord une information manquante.")
        return r

    def formules(self) -> pd.DataFrame:
        c = self.modele.m1x2.coefficients().join(self.modele.buts.coefficients(), how="outer")
        return c.loc[["constante"] + self.modele.buts.cols]
