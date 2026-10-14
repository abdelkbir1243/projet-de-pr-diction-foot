"""Contexte d'avant-match : repos, enchaînement des matchs, phase de saison, statut (promu, première saison, champion en titre)
et enjeu au classement (course au titre, places européennes, maintien, fin de saison sans enjeu).

Tout est calculé avec l'information disponible AVANT le coup d'envoi : le classement utilisé est celui de la veille du match.
Les mêmes fonctions servent à l'apprentissage (tous les matchs historiques) et à la prédiction d'un match à venir.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd

from .equipes import PAR_CODE

REPOS_MAX = 14            # au-delà, le repos n'apporte plus d'information (trêve internationale, début de saison)
FENETRE_CHARGE = 21       # jours pris en compte pour la charge de matchs
DEBUT_SAISON = 6          # nombre de matchs joués en deçà duquel on est « en début de saison » (mercato, effectifs instables)
FIN_SAISON = 8            # matchs restants à partir desquels l'enjeu au classement est évalué
ECART_ENJEU = 6           # points : un objectif est « en jeu » si l'écart est inférieur ou égal


@dataclass
class Table:
    """Classement d'une ligue pour une saison, mis à jour match après match."""
    pts: dict
    j: dict
    bp: dict
    bc: dict

    @classmethod
    def vide(cls, equipes):
        z = lambda: {e: 0 for e in equipes}
        return cls(z(), z(), z(), z())

    def ajouter(self, h, a, gh, ga):
        for e in (h, a):
            for d in (self.pts, self.j, self.bp, self.bc):
                d.setdefault(e, 0)
        self.j[h] += 1; self.j[a] += 1
        self.bp[h] += gh; self.bc[h] += ga; self.bp[a] += ga; self.bc[a] += gh
        self.pts[h] += 3 if gh > ga else (1 if gh == ga else 0)
        self.pts[a] += 3 if ga > gh else (1 if gh == ga else 0)

    def ordre(self):
        return sorted(self.pts, key=lambda e: (-self.pts[e], -(self.bp[e] - self.bc[e]), -self.bp[e], e))


def zones(division: str, n_equipes: int) -> dict:
    z = PAR_CODE.get(division, {}).get("zones", {}) or {}
    cl = z.get("cl", [1, 4]); el = z.get("el", [cl[1] + 1, cl[1] + 2]); rel = z.get("rel", [n_equipes - 2, n_equipes])
    rel = [n_equipes - (rel[1] - rel[0]), n_equipes]                 # 18 ou 20 équipes : la zone suit le nombre d'équipes
    return {"europe": el[1], "rel": rel[0]}


def enjeu(table: Table, equipe: str, n_equipes: int, division: str) -> dict:
    """Situation d'une équipe au classement : écarts aux objectifs et motivation estimée (fin de saison uniquement)."""
    if not table.j.get(equipe):
        return {"rang": None, "titre": 0.0, "europe": 0.0, "maintien": 0.0, "sans_enjeu": 0.0, "restants": 2 * (n_equipes - 1), "ecart_tete": None,
                "ecart_maintien": None}
    o = table.ordre(); rang = o.index(equipe) + 1; z = zones(division, n_equipes)
    p = table.pts[equipe]; restants = max(0, 2 * (n_equipes - 1) - table.j[equipe])
    pts_rang = lambda r: table.pts[o[min(r, len(o)) - 1]]
    ecart_tete = pts_rang(1) - p if rang > 1 else p - pts_rang(2)          # leader : avance sur le 2e (positif)
    ecart_europe = pts_rang(z["europe"]) - p                               # > 0 : points à reprendre pour entrer dans l'Europe
    marge_maintien = p - pts_rang(z["rel"])                                # > 0 : avance sur le premier relégable
    out = {"rang": rang, "restants": restants, "ecart_tete": int(ecart_tete), "ecart_maintien": int(marge_maintien),
           "titre": 0.0, "europe": 0.0, "maintien": 0.0, "sans_enjeu": 0.0}
    if restants > FIN_SAISON:
        return out
    possible = lambda ecart: ecart <= 3 * restants
    out["titre"] = float((rang == 1 and ecart_tete <= ECART_ENJEU) or (rang > 1 and ecart_tete <= ECART_ENJEU and possible(ecart_tete)))
    out["europe"] = float(not out["titre"] and abs(ecart_europe) <= ECART_ENJEU and possible(max(ecart_europe, 0)))
    out["maintien"] = float(marge_maintien <= ECART_ENJEU and possible(-min(marge_maintien, 0)))
    out["sans_enjeu"] = float(not (out["titre"] or out["europe"] or out["maintien"]))
    return out


def statut_saison(D: pd.DataFrame) -> dict:
    """(division, saison, équipe) → promu, première saison dans la division, champion en titre."""
    eq = D.groupby(["Division", "Season"]).apply(lambda d: set(d.HomeTeam) | set(d.AwayTeam), include_groups=False).to_dict()
    champions = {}
    for (lg, s), d in D.groupby(["Division", "Season"]):
        t = Table.vide(eq[(lg, s)])
        for r in d.itertuples():
            t.ajouter(r.HomeTeam, r.AwayTeam, r.FTHome, r.FTAway)
        champions[(lg, s)] = t.ordre()[0]
    deja = {}
    out = {}
    for (lg, s) in sorted(eq, key=lambda k: k[1]):
        prev = eq.get((lg, s - 1))
        for e in eq[(lg, s)]:
            out[(lg, s, e)] = {"promu": float(prev is not None and e not in prev), "premiere": float(prev is not None and e not in deja.get(lg, set())),
                               "champion": float(champions.get((lg, s - 1)) == e)}
        deja.setdefault(lg, set()).update(eq[(lg, s)])
    return out


def statut_equipe(Dlg: pd.DataFrame, s: int, e: str) -> dict:
    """Statut d'une équipe pour la saison s d'une division (Dlg = matchs de cette division), même si la saison n'a pas commencé."""
    avant = Dlg[Dlg.Season < s]
    prev = avant[avant.Season == s - 1]
    eq_prev = set(prev.HomeTeam) | set(prev.AwayTeam)
    champion = None
    if len(prev):
        t = Table.vide(eq_prev)
        for r in prev.itertuples():
            t.ajouter(r.HomeTeam, r.AwayTeam, r.FTHome, r.FTAway)
        champion = t.ordre()[0]
    return {"promu": float(bool(eq_prev) and e not in eq_prev), "premiere": float(bool(len(avant)) and e not in set(avant.HomeTeam) | set(avant.AwayTeam)),
            "champion": float(champion == e)}


def calculer(R: pd.DataFrame, D: pd.DataFrame) -> pd.DataFrame:
    """Variables de contexte de chaque match de D (index = mid), suffixes _h (domicile) et _a (extérieur).

    R : tous les matchs connus (toutes divisions) pour le repos ; D : matchs des 5 ligues, colonne mid, triés ou non.
    """
    # repos et charge : dernier match connu de l'équipe, toutes divisions du dataset confondues
    long = pd.concat([R[["MatchDate", "HomeTeam"]].rename(columns={"HomeTeam": "team"}), R[["MatchDate", "AwayTeam"]].rename(columns={"AwayTeam": "team"})])
    long = long.dropna().drop_duplicates().sort_values(["team", "MatchDate"])
    dates = {t: g.MatchDate.values for t, g in long.groupby("team")}

    def repos_charge(team, date):
        d = dates.get(team)
        if d is None:
            return REPOS_MAX, 0
        i = np.searchsorted(d, np.datetime64(date), side="left")            # matchs strictement antérieurs
        if i == 0:
            return REPOS_MAX, 0
        rep = (np.datetime64(date) - d[i - 1]) / np.timedelta64(1, "D")
        j = np.searchsorted(d, np.datetime64(date) - np.timedelta64(FENETRE_CHARGE, "D"), side="left")
        return float(min(rep, REPOS_MAX)), int(i - j)

    statut = statut_saison(D)
    rows = []
    for (lg, s), d in D.sort_values(["MatchDate", "mid"]).groupby(["Division", "Season"], sort=False):
        equipes = set(d.HomeTeam) | set(d.AwayTeam); n = len(equipes)
        t = Table.vide(equipes)
        for jour, dj in d.groupby("MatchDate", sort=True):
            # tous les matchs d'une même journée voient le classement de la veille
            for r in dj.itertuples():
                row = {"mid": r.mid}
                for suf, e in (("h", r.HomeTeam), ("a", r.AwayTeam)):
                    rep, ch = repos_charge(e, jour)
                    en = enjeu(t, e, n, lg)
                    st = statut.get((lg, s, e), {"promu": 0.0, "premiere": 0.0, "champion": 0.0})
                    row |= {f"repos_{suf}": rep, f"charge_{suf}": ch, f"joues_{suf}": t.j.get(e, 0), f"rang_{suf}": en["rang"],
                            f"titre_{suf}": en["titre"], f"europe_{suf}": en["europe"], f"maintien_{suf}": en["maintien"],
                            f"sansenjeu_{suf}": en["sans_enjeu"], **{f"{k}_{suf}": v for k, v in st.items()}}
                rows.append(row)
            for r in dj.itertuples():
                t.ajouter(r.HomeTeam, r.AwayTeam, r.FTHome, r.FTAway)
    K = pd.DataFrame(rows).set_index("mid")
    return ajouter_derivees(K)


def ajouter_derivees(K: pd.DataFrame) -> pd.DataFrame:
    """Variables utilisées par le modèle, construites à partir des variables brutes de contexte."""
    rh, ra = np.clip(K.repos_h, 2, 10), np.clip(K.repos_a, 2, 10)
    K["dRepos"] = (rh - ra) / 7                                          # en semaines de repos
    K["court_h"], K["court_a"] = (K.repos_h <= 3).astype(float), (K.repos_a <= 3).astype(float)
    K["debut"] = (np.minimum(K.joues_h, K.joues_a) < DEBUT_SAISON).astype(float)
    K["dPromu"] = K.promu_h - K.promu_a
    K["dChampion"] = K.champion_h - K.champion_a
    K["dMotiv"] = (K.titre_h + K.europe_h + K.maintien_h - K.sansenjeu_h) - (K.titre_a + K.europe_a + K.maintien_a - K.sansenjeu_a)
    K["enjeu2"] = ((K.titre_h + K.europe_h + K.maintien_h > 0) & (K.titre_a + K.europe_a + K.maintien_a > 0)).astype(float)
    K["sansenjeu2"] = K.sansenjeu_h * K.sansenjeu_a
    return K


# Écart moyen (points par match) entre les points obtenus et les points attendus par le modèle v4, matchs 2010-2025
# hors échantillon (walk-forward). Seuls les effets significatifs sont cités dans l'interface. Voir docs/resultats.md.
EFFETS = {"titre": +0.14, "maintien": +0.08, "sans_enjeu": -0.06, "sans_enjeu_vs_enjeu": -0.11}


def description(k: dict, nom: str, dom: bool) -> list[str]:
    """Phrases lisibles du contexte d'une équipe (pour l'interface)."""
    s = "h" if dom else "a"; out = []
    if k.get(f"premiere_{s}"):
        out.append(f"{nom} découvre ce championnat (première saison au moins depuis 2005/06)")
    elif k.get(f"promu_{s}"):
        out.append(f"{nom} est promu cette saison")
    if k.get(f"champion_{s}"):
        out.append(f"{nom} est le champion en titre")
    if k.get(f"titre_{s}"):
        out.append(f"{nom} est à la lutte pour le titre (historiquement +{EFFETS['titre']:.2f} pt/match au-delà du niveau attendu)".replace(".", ","))
    if k.get(f"europe_{s}"):
        out.append(f"{nom} joue une place européenne")
    if k.get(f"maintien_{s}"):
        out.append(f"{nom} joue son maintien (historiquement +{EFFETS['maintien']:.2f} pt/match au-delà du niveau attendu)".replace(".", ","))
    if k.get(f"sansenjeu_{s}"):
        out.append(f"{nom} n'a plus d'objectif majeur au classement (historiquement {EFFETS['sans_enjeu']:.2f} pt/match)".replace(".", ","))
    rep = k.get(f"repos_{s}")
    if rep is not None and rep <= 3:
        out.append(f"{nom} a eu seulement {int(rep)} jours de repos")
    if k.get(f"charge_{s}", 0) >= 5:
        out.append(f"{nom} a joué {int(k[f'charge_{s}'])} matchs en 21 jours")
    return out
