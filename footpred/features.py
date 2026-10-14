"""Variables d'avant-match (sans fuite) pour les 5 grands championnats.

Toutes les moyennes glissantes sont décalées d'un match (shift(1)) : la ligne d'un match ne contient que de l'information
disponible avant son coup d'envoi. tests/test_fuite.py le vérifie automatiquement.
"""
import difflib
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from . import config as C
from .ratings import PiRatings, GasRatings
from . import contexte as K


@dataclass
class Donnees:
    X: pd.DataFrame                  # une ligne par match (index = mid), variables + résultats
    L: pd.DataFrame                  # table longue : une ligne par (équipe, match)
    D: pd.DataFrame                  # matchs des 5 ligues
    pi: PiRatings
    gas: GasRatings
    c_L: pd.Series                   # buts par tir cadré, par (ligue, saison), estimé sur les saisons antérieures
    date_max: pd.Timestamp = field(default=None)
    R: pd.DataFrame = field(default=None)       # tous les matchs connus (toutes divisions) : repos et charge des équipes
    _statut: dict = field(default_factory=dict, repr=False)
    D_all: pd.DataFrame = field(default=None)   # 5 ligues + deuxièmes divisions (forme des promus, profils)

    def ligue_match(self, dom: str, ext: str) -> str:
        """Championnat d'un match à venir : celui de l'équipe à domicile si elle y joue, sinon celui de l'adversaire."""
        for e in (dom, ext):
            t = self.L[self.L.team == e]
            if len(t) and t.Division.iloc[-1] in C.LIGUES:
                return t.Division.iloc[-1]
        t = self.L[self.L.team == dom]
        return C.DIV2.get(t.Division.iloc[-1], C.LIGUE_REF) if len(t) else C.LIGUE_REF

    # ---------- contexte d'un match à venir (repos, statut, enjeu) ----------
    def contexte(self, dom: str, ext: str, jour=None, lg=None) -> dict:
        jour = pd.Timestamp(jour or (self.date_max + pd.Timedelta(days=1))).normalize()
        lg = lg or self.ligue_match(dom, ext)
        s = jour.year if jour.month >= 7 else jour.year - 1                  # saison du match (même avant la 1re journée)
        d = self.D[(self.D.Division == lg) & (self.D.Season == s) & (self.D.MatchDate < jour)]
        equipes = set(d.HomeTeam) | set(d.AwayTeam) | {dom, ext}
        prev = self.D[(self.D.Division == lg) & (self.D.Season == s - 1)]
        n = max(len(equipes), prev.HomeTeam.nunique() or 18)        # nombre d'équipes de la division
        t = K.Table.vide(equipes)
        for r in d.itertuples():
            t.ajouter(r.HomeTeam, r.AwayTeam, r.FTHome, r.FTAway)
        R = self.R if self.R is not None else self.D
        out = {}
        for suf, e in (("h", dom), ("a", ext)):
            dates = pd.concat([R.MatchDate[R.HomeTeam == e], R.MatchDate[R.AwayTeam == e]])
            dates = dates[dates < jour]
            rep = float(min((jour - dates.max()).days, K.REPOS_MAX)) if len(dates) else K.REPOS_MAX
            ch = int((dates >= jour - pd.Timedelta(days=K.FENETRE_CHARGE)).sum())
            en = K.enjeu(t, e, n, lg)
            if (lg, s, e) not in self._statut:
                self._statut[(lg, s, e)] = K.statut_equipe(self.D[self.D.Division == lg], s, e)
            st = self._statut[(lg, s, e)]
            out |= {f"repos_{suf}": rep, f"charge_{suf}": ch, f"joues_{suf}": t.j.get(e, 0), f"rang_{suf}": en["rang"],
                    f"titre_{suf}": en["titre"], f"europe_{suf}": en["europe"], f"maintien_{suf}": en["maintien"],
                    f"sansenjeu_{suf}": en["sans_enjeu"], f"restants_{suf}": en["restants"], f"ecart_tete_{suf}": en["ecart_tete"],
                    f"ecart_maintien_{suf}": en["ecart_maintien"], **{f"{k}_{suf}": v for k, v in st.items()}}
        return motivation(out)

    # ---------- état d'une équipe pour prédire un match à venir ----------
    def etat(self, equipe: str, lg: str | None = None) -> dict:
        t = self.L[self.L.team == equipe].sort_values("date")
        if t.empty:
            proches = difflib.get_close_matches(equipe, self.L.team.unique(), 5)
            raise ValueError(f"Équipe inconnue : « {equipe} ». Noms proches : {proches}")
        last = t.tail(C.FENETRE_FORME)
        lg = lg or (t.Division.iloc[-1] if t.Division.iloc[-1] in C.LIGUES else C.DIV2.get(t.Division.iloc[-1], C.LIGUE_REF))
        s_cur = int(self.D.Season.max())
        joues = int(((self.D.HomeTeam == equipe) | (self.D.AwayTeam == equipe))[self.D.Season == s_cur].sum())
        n_eq = self.D[(self.D.Division == lg) & (self.D.Season == s_cur)].HomeTeam.nunique() or 20
        lgm = self.D[self.D.Division == lg].tail(C.FENETRE_LIGUE)
        return {"elo": t.elo.dropna().iloc[-1], "Q": last.xg_f.mean() - last.xg_a.mean(), "O": last.xg_f.mean() + last.xg_a.mean(),
                "pi": self.pi.note(equipe), "lg": lg, "date": t.date.iloc[-1].date(),
                "lg_mh": lgm.FTHome.mean(), "lg_ma": lgm.FTAway.mean(), "restants": 2 * (n_eq - 1) - joues,
                "stats": {k: last[k].mean() for k in C.STATS_EQUIPE},
                "lg_c": (lgm.HomeCorners + lgm.AwayCorners).mean(), "lg_y": (lgm.HomeYellow + lgm.AwayYellow).mean(),
                "lg_r": (lgm.HomeRed + lgm.AwayRed).mean()}

    def variables_match(self, dom: str, ext: str, elo_dom=None, elo_ext=None, jour=None, lg=None) -> tuple[dict, dict, dict]:
        """Construit le vecteur de variables d'un match à venir (même définition que pour l'apprentissage)."""
        lg = lg or self.ligue_match(dom, ext)
        a, b = self.etat(dom, lg), self.etat(ext, lg)
        a["contexte"] = b["contexte"] = self.contexte(dom, ext, jour, lg)
        ea, eb = elo_dom or a["elo"], elo_ext or b["elo"]
        v = {"dElo": (ea - eb) / 100, "dQ": a["Q"] - b["Q"], "Otot": a["O"] + b["O"] - C.OUVERTURE_CENTRE,
             "pi_diff": a["pi"][0] - b["pi"][1], "pi_diff_avg": np.mean(a["pi"]) - np.mean(b["pi"])}
        v["absElo"] = abs(v["dElo"])
        for lg in C.LIGUES:
            if lg != C.LIGUE_REF:
                v[f"lg_{lg}"] = float(a["lg"] == lg)
        v["g_lh"], v["g_la"] = self.gas.log_lambdas(dom, ext, lg)
        v["lg_mh_c"], v["lg_ma_c"] = a["lg_mh"] - C.CENTRE_BUTS[0], a["lg_ma"] - C.CENTRE_BUTS[1]
        for k in C.STATS_EQUIPE:
            v[f"h_{k}"], v[f"a_{k}"] = a["stats"][k], b["stats"][k]
        v["l_lg_c"], v["l_lg_y"], v["l_lg_r"] = np.log(a["lg_c"]), np.log(a["lg_y"]), np.log(a["lg_r"])
        v |= {k: a["contexte"][k] for k in C.MOTIVATION}
        v["_elo_dom"], v["_elo_ext"] = ea, eb
        return v, a, b


def motivation(k):
    """Variables d'enjeu utilisées par le modèle v5 (dict ou DataFrame de contexte)."""
    k["motiv_h"], k["motiv_a"] = k["titre_h"] + k["maintien_h"], k["titre_a"] + k["maintien_a"]
    return k


def construire(raw: pd.DataFrame, contexte: bool = True) -> Donnees:
    # 1. ratings sur toutes les ligues, ordre chronologique
    R = raw.dropna(subset=["HomeTeam", "AwayTeam"]).sort_values("MatchDate", kind="stable").reset_index(drop=True)
    pi, gas = PiRatings(), GasRatings()
    R[["pi_hh", "pi_ha", "pi_ah", "pi_aa"]] = pi.calculer(R)
    R[["g_lh", "g_la"]] = gas.calculer(R)

    # 2. 5 grands championnats (+ deuxièmes divisions pour la forme des promus), table longue équipe-match
    DA = R[R.Division.isin(list(C.LIGUES) + list(C.DIV2)) & (R.Season >= C.SAISON_MIN)].dropna(subset=["FTResult"]).reset_index(drop=True)
    DA["mid"] = np.arange(len(DA)); DA["y"] = DA.FTResult.map({"H": 0, "D": 1, "A": 2})
    D = DA[DA.Division.isin(C.LIGUES)].reset_index(drop=True)

    def side(home):
        s, o = ("Home", "Away") if home else ("Away", "Home")
        return pd.DataFrame({"mid": DA.mid, "date": DA.MatchDate, "Division": DA.Division, "team": DA[f"{s}Team"], "home": int(home),
                             "gf": DA[f"FT{s}"], "ga": DA[f"FT{o}"], "sot_f": DA[f"{s}Target"], "sot_a": DA[f"{o}Target"], "elo": DA[f"{s}Elo"],
                             "cf": DA[f"{s}Corners"], "ca": DA[f"{o}Corners"], "yf": DA[f"{s}Yellow"], "ya": DA[f"{o}Yellow"],
                             "rf": DA[f"{s}Red"], "ra": DA[f"{o}Red"], "ff": DA[f"{s}Fouls"], "fa": DA[f"{o}Fouls"],
                             "sf": DA[f"{s}Shots"], "sa": DA[f"{o}Shots"]})
    L = pd.concat([side(True), side(False)]).sort_values(["team", "date", "mid"]).reset_index(drop=True)
    # xG approché = c × tirs cadrés ; c (buts par tir cadré) estimé sur les SAISONS PRÉCÉDENTES de la ligue uniquement
    H5 = R[R.Division.isin(list(C.LIGUES) + list(C.DIV2))].dropna(subset=["FTHome", "HomeTarget"])
    tot = pd.DataFrame({"g": H5.FTHome + H5.FTAway, "t": H5.HomeTarget + H5.AwayTarget, "Division": H5.Division, "Season": H5.Season}) \
        .groupby(["Division", "Season"]).sum()
    prev = tot.groupby(level=0).cumsum() - tot
    c_L = (prev.g / prev.t.where(prev.t > 0)).fillna(C.CONVERSION_DEFAUT)
    cs = pd.Series(list(zip(DA.Division, DA.Season)), index=DA.mid).map(c_L)
    L["xg_f"], L["xg_a"] = L.sot_f * L.mid.map(cs), L.sot_a * L.mid.map(cs)
    g = L.groupby("team")
    mf = g.xg_f.transform(lambda x: x.shift(1).rolling(C.FENETRE_FORME, min_periods=5).mean())
    ma = g.xg_a.transform(lambda x: x.shift(1).rolling(C.FENETRE_FORME, min_periods=5).mean())
    L["Q"], L["O"] = mf - ma, mf + ma
    # moyennes des 10 derniers matchs (corners, cartons, fautes, tirs), décalées d'un match
    roll = g[C.STATS_EQUIPE].transform(lambda x: x.shift(1).rolling(C.FENETRE_FORME, min_periods=5).mean())

    # 3. variables du match
    H, A = L[L.home == 1].set_index("mid"), L[L.home == 0].set_index("mid")
    X = D.set_index("mid")
    X["dElo"] = (X.HomeElo - X.AwayElo) / 100; X["absElo"] = X.dElo.abs()
    X["dQ"] = H.Q - A.Q; X["Otot"] = H.O + A.O - C.OUVERTURE_CENTRE
    X["pi_diff"] = X.pi_hh - X.pi_aa; X["pi_diff_avg"] = (X.pi_hh + X.pi_ha) / 2 - (X.pi_ah + X.pi_aa) / 2
    for lg in C.LIGUES:
        if lg != C.LIGUE_REF:
            X[f"lg_{lg}"] = (X.Division == lg).astype(float)
    Dm = D.sort_values(["Division", "MatchDate", "mid"])
    for c, col in (("lg_mh", "FTHome"), ("lg_ma", "FTAway")):
        Dm[c] = Dm.groupby("Division")[col].transform(lambda x: x.shift(1).rolling(C.FENETRE_LIGUE, min_periods=150).mean())
    X = X.join(Dm.set_index("mid")[["lg_mh", "lg_ma"]])
    X["lg_mh_c"], X["lg_ma_c"] = X.lg_mh - C.CENTRE_BUTS[0], X.lg_ma - C.CENTRE_BUTS[1]
    # corners et cartons : variables d'équipe (h_ = domicile, a_ = extérieur) et niveau de la ligue
    roll[["mid", "home"]] = L[["mid", "home"]]
    X = X.join(roll[roll.home == 1].set_index("mid")[C.STATS_EQUIPE].add_prefix("h_")).join(roll[roll.home == 0].set_index("mid")[C.STATS_EQUIPE].add_prefix("a_"))
    Dm["c_tot"], Dm["y_tot"], Dm["r_tot"] = Dm.HomeCorners + Dm.AwayCorners, Dm.HomeYellow + Dm.AwayYellow, Dm.HomeRed + Dm.AwayRed
    for c, k in (("c_tot", "l_lg_c"), ("y_tot", "l_lg_y"), ("r_tot", "l_lg_r")):
        Dm[k] = np.log(Dm.groupby("Division")[c].transform(lambda x: x.shift(1).rolling(C.FENETRE_LIGUE, min_periods=150).mean()))
    X = X.join(Dm.set_index("mid")[["c_tot", "y_tot", "r_tot", "l_lg_c", "l_lg_y", "l_lg_r"]])
    # 4. contexte : repos, statut, enjeu au classement (classement de la veille du match)
    if contexte:
        X = X.join(motivation(K.calculer(R, D)))
    else:
        for c in C.MOTIVATION:
            X[c] = 0.0
    X = X.dropna(subset=C.FE_B)
    return Donnees(X=X, L=L, D=D, pi=pi, gas=gas, c_L=c_L, date_max=raw.MatchDate.max(), R=R[["MatchDate", "HomeTeam", "AwayTeam"]], D_all=DA)
