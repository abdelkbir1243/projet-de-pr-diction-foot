"""Statistiques descriptives : profil d'une équipe, comparaison avec la ligue, confrontations directes."""
import numpy as np
import pandas as pd

INDICATEURS = [  # (libellé, colonne « pour » côté domicile, colonne « pour » côté extérieur)
    ("Buts marqués", "FTHome", "FTAway"), ("Tirs", "HomeShots", "AwayShots"), ("Tirs cadrés", "HomeTarget", "AwayTarget"),
    ("Corners obtenus", "HomeCorners", "AwayCorners"), ("Cartons jaunes", "HomeYellow", "AwayYellow"),
    ("Cartons rouges", "HomeRed", "AwayRed"), ("Fautes commises", "HomeFouls", "AwayFouls"),
]


def matchs_equipe(D: pd.DataFrame, equipe: str, n: int | None = 10, lieu: str = "tous") -> pd.DataFrame:
    """Derniers matchs d'une équipe, vus de son côté (pour / contre). lieu ∈ {tous, domicile, extérieur}."""
    parts = []
    if lieu in ("tous", "domicile"):
        h = D[D.HomeTeam == equipe]
        parts.append(pd.DataFrame({"date": h.MatchDate, "adversaire": h.AwayTeam, "lieu": "dom", "Division": h.Division,
                                   **{f"{k}_pour": h[a] for k, a, b in INDICATEURS}, **{f"{k}_contre": h[b] for k, a, b in INDICATEURS}}))
    if lieu in ("tous", "extérieur"):
        a_ = D[D.AwayTeam == equipe]
        parts.append(pd.DataFrame({"date": a_.MatchDate, "adversaire": a_.HomeTeam, "lieu": "ext", "Division": a_.Division,
                                   **{f"{k}_pour": a_[b] for k, a, b in INDICATEURS}, **{f"{k}_contre": a_[a] for k, a, b in INDICATEURS}}))
    M = pd.concat(parts).sort_values("date")
    M = M if n is None else M.tail(n)
    M["résultat"] = np.select([M["Buts marqués_pour"] > M["Buts marqués_contre"], M["Buts marqués_pour"] == M["Buts marqués_contre"]], ["V", "N"], "D")
    return M


def profil(D: pd.DataFrame, equipe: str, n: int | None = 10, lieu: str = "tous") -> pd.Series:
    M = matchs_equipe(D, equipe, n, lieu)
    tot_b = M["Buts marqués_pour"] + M["Buts marqués_contre"]
    tot_c = M["Corners obtenus_pour"] + M["Corners obtenus_contre"]
    tot_j = M["Cartons jaunes_pour"] + M["Cartons jaunes_contre"]
    s = {"matchs": len(M), "victoires": (M["résultat"] == "V").mean(), "nuls": (M["résultat"] == "N").mean(), "défaites": (M["résultat"] == "D").mean(),
         "points par match": ((M["résultat"] == "V") * 3 + (M["résultat"] == "N")).mean()}
    for k, _, _ in INDICATEURS:
        s[f"{k} (pour)"] = M[f"{k}_pour"].mean(); s[f"{k} (contre)"] = M[f"{k}_contre"].mean()
    s.update({"% plus de 2,5 buts": (tot_b > 2.5).mean(), "% les deux marquent": ((M["Buts marqués_pour"] > 0) & (M["Buts marqués_contre"] > 0)).mean(),
              "% cage inviolée": (M["Buts marqués_contre"] == 0).mean(), "% plus de 9,5 corners": (tot_c > 9.5).mean(),
              "% plus de 4,5 jaunes": (tot_j > 4.5).mean(), "forme (5 derniers)": "".join(M["résultat"].tail(5))})
    return pd.Series(s, name=equipe)


def profil_ligue(D: pd.DataFrame, ligue: str, n: int = 380) -> pd.Series:
    L = D[D.Division == ligue].tail(n)
    s = {"matchs": len(L), "victoires": (L.FTHome > L.FTAway).mean(), "nuls": (L.FTHome == L.FTAway).mean(), "défaites": (L.FTHome < L.FTAway).mean(),
         "points par match": np.nan}
    for k, a, b in INDICATEURS:
        s[f"{k} (pour)"] = (L[a].mean() + L[b].mean()) / 2; s[f"{k} (contre)"] = s[f"{k} (pour)"]
    s.update({"% plus de 2,5 buts": (L.FTHome + L.FTAway > 2.5).mean(), "% les deux marquent": ((L.FTHome > 0) & (L.FTAway > 0)).mean(),
              "% cage inviolée": ((L.FTAway == 0).mean() + (L.FTHome == 0).mean()) / 2, "% plus de 9,5 corners": (L.HomeCorners + L.AwayCorners > 9.5).mean(),
              "% plus de 4,5 jaunes": (L.HomeYellow + L.AwayYellow > 4.5).mean(), "forme (5 derniers)": ""})
    return pd.Series(s, name="moyenne de la ligue")


def comparaison(D, dom, ext, n=10):
    """Domicile (matchs à domicile), extérieur (matchs à l'extérieur), et moyenne de la ligue."""
    lg = D[(D.HomeTeam == dom) | (D.AwayTeam == dom)].Division.iloc[-1]
    return pd.concat([profil(D, dom, n, "domicile").rename(f"{dom} (à domicile)"), profil(D, ext, n, "extérieur").rename(f"{ext} (à l'extérieur)"),
                      profil(D, dom, n).rename(f"{dom} (tous)"), profil(D, ext, n).rename(f"{ext} (tous)"), profil_ligue(D, lg)], axis=1)


def confrontations(D, a, b, n=10) -> pd.DataFrame:
    H = D[((D.HomeTeam == a) & (D.AwayTeam == b)) | ((D.HomeTeam == b) & (D.AwayTeam == a))].sort_values("MatchDate").tail(n)
    return pd.DataFrame({"date": H.MatchDate.dt.date, "domicile": H.HomeTeam, "extérieur": H.AwayTeam,
                         "score": H.FTHome.astype(int).astype(str) + "-" + H.FTAway.astype(int).astype(str),
                         "corners": (H.HomeCorners.astype("Int64").astype(str) + "-" + H.AwayCorners.astype("Int64").astype(str)),
                         "jaunes": (H.HomeYellow.astype("Int64").astype(str) + "-" + H.AwayYellow.astype("Int64").astype(str)),
                         "rouges": (H.HomeRed.astype("Int64").astype(str) + "-" + H.AwayRed.astype("Int64").astype(str))}).iloc[::-1].reset_index(drop=True)
