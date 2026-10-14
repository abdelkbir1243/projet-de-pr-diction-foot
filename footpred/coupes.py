"""Coupes d'Europe : Ligue des champions, Ligue Europa, Conference League.

Source gratuite : openfootball/champions-league (GitHub, format texte), Ligue des champions depuis 2011/12, Ligue Europa
depuis 2020/21, Conference League depuis 2021/22. Le calendrier et les scores en direct de la Ligue des champions viennent
aussi de football-data.org quand une clé est configurée.

Modèle « coupes » : les équipes viennent de championnats différents, donc les variables propres à une ligue (pi-ratings,
ratings de buts, forme en xG) ne sont pas comparables. On utilise l'Elo de ClubElo, calibré pour toute l'Europe, présent dans
le dataset pour les clubs des championnats couverts. Pour les autres clubs (Ukraine, Croatie, Serbie…), un Elo est estimé à
partir de leurs seuls matchs européens. Logit multinomial (1X2) et Poisson + Dixon-Coles (buts) sur ces variables, évalués
saison par saison sur des coupes que le modèle n'avait pas vues (docs/resultats.md §15).
"""
import os
import re
import urllib.request
from datetime import date, datetime

import numpy as np
import pandas as pd

from .equipes import associer, nom, slug
from .evaluation import log_loss, brier, ece, rps, ic_bootstrap
from .markets import marches, scores_probables
from .models import Modele1X2, ModeleButs, grille

BASE = "https://raw.githubusercontent.com/openfootball/champions-league/master"
COUPES = {  # code openfootball → (code interne, nom, slug)
    "cl": ("CL", "Ligue des champions", "champions-league"),
    "el": ("EL", "Ligue Europa", "europa-league"),
    "conf": ("ECL", "Conference League", "conference-league"),
}
# pays (code openfootball) → divisions du dataset où chercher le club
PAYS = {"ENG": ["E0", "E1", "E2", "E3", "EC"], "ESP": ["SP1", "SP2"], "ITA": ["I1", "I2"], "GER": ["D1", "D2"], "FRA": ["F1", "F2"],
        "NED": ["N1"], "POR": ["P1"], "BEL": ["B1"], "TUR": ["T1"], "GRE": ["G1"], "SCO": ["SC0", "SC1", "SC2", "SC3"],
        "AUT": ["AUT"], "SUI": ["SUI"], "DEN": ["DEN"], "NOR": ["NOR"], "SWE": ["SWE"], "POL": ["POL"], "ROU": ["ROM"],
        "RUS": ["RUS"], "FIN": ["FIN"], "IRL": ["IRL"], "MCO": ["F1", "F2"]}
ALIAS = {"bayern munchen": "Bayern Munich", "fc bayern munchen": "Bayern Munich", "club brugge kv": "Club Brugge", "club brugge": "Club Brugge",
         "sport lisboa e benfica": "Benfica", "sporting clube de portugal": "Sp Lisbon", "sporting cp": "Sp Lisbon", "fc porto": "Porto",
         "psv": "PSV Eindhoven", "afc ajax": "Ajax", "ajax": "Ajax", "az alkmaar": "AZ Alkmaar",
         "feyenoord rotterdam": "Feyenoord", "galatasaray": "Galatasaray", "fenerbahce": "Fenerbahce", "besiktas": "Besiktas",
         "olympiacos": "Olympiakos", "olympiacos piraeus": "Olympiakos", "paok": "PAOK", "celtic": "Celtic", "rangers": "Rangers",
         "manchester city": "Man City", "manchester united": "Man United", "tottenham hotspur": "Tottenham", "newcastle united": "Newcastle",
         "west ham united": "West Ham", "aston villa": "Aston Villa", "paris saint germain": "Paris SG", "olympique lyonnais": "Lyon",
         "olympique de marseille": "Marseille", "stade rennais": "Rennes", "losc lille": "Lille", "lille osc": "Lille", "as monaco": "Monaco",
         "ogc nice": "Nice", "internazionale milano": "Inter", "inter": "Inter", "ac milan": "Milan", "as roma": "Roma", "ss lazio": "Lazio",
         "ssc napoli": "Napoli", "atalanta bc": "Atalanta", "atletico madrid": "Ath Madrid", "club atletico de madrid": "Ath Madrid",
         "athletic club": "Ath Bilbao", "real betis": "Betis", "real sociedad": "Sociedad", "borussia monchengladbach": "M'gladbach",
         "eintracht frankfurt": "Ein Frankfurt", "bayer leverkusen": "Leverkusen", "bayer 04 leverkusen": "Leverkusen",
         "vfb stuttgart": "Stuttgart", "rb leipzig": "RB Leipzig", "tsg hoffenheim": "Hoffenheim", "union berlin": "Union Berlin",
         "rb salzburg": "Salzburg", "red bull salzburg": "Salzburg", "fc red bull salzburg": "Salzburg", "sk sturm graz": "Sturm Graz",
         "rapid wien": "Rapid Vienna", "bsc young boys": "Young Boys", "fc basel 1893": "Basel", "fc kobenhavn": "FC Copenhagen",
         "fc copenhagen": "FC Copenhagen", "fc midtjylland": "Midtjylland", "malmo ff": "Malmo FF", "fk bodo glimt": "Bodo/Glimt",
         "bodo glimt": "Bodo/Glimt", "brondby": "Brondby", "brondby if": "Brondby", "kobenhavn": "FC Copenhagen", "fc kobenhavn": "FC Copenhagen",
         "cska moskva": "CSKA Moscow", "spartak moskva": "Spartak Moscow", "rapid wien": "SK Rapid", "sk rapid wien": "SK Rapid",
         "union saint gilloise": "St. Gilloise", "royale union saint gilloise": "St. Gilloise", "sporting braga": "Sp Braga",
         "sporting clube de braga": "Sp Braga", "sc braga": "Sp Braga", "braga": "Sp Braga", "heart of midlothian": "Hearts",
         "istanbul basaksehir": "Buyuksehyr", "basaksehir": "Buyuksehyr", "steaua bucuresti": "FCSB", "fc steaua bucuresti": "FCSB", "fcsb": "FCSB",
         "monaco": "Monaco", "as monaco": "Monaco"}
CASSE = {"knockout": ("round of", "quarter", "semi", "final", "playoff", "play-off", "knockout", "achtel", "viertel", "halb")}


# ---------------------------------------------------------------- téléchargement et lecture du format openfootball
def saisons_disponibles(premiere=2011, derniere=None) -> list[str]:
    derniere = derniere or (date.today().year if date.today().month >= 7 else date.today().year - 1)
    return [f"{y}-{(y + 1) % 100:02d}" for y in range(premiere, derniere + 1)]


def telecharger(dossier: str | None = None, saisons=None) -> dict[tuple[str, str], str]:
    """{(coupe, saison): texte}. Les fichiers absents (saison non publiée) sont ignorés ; cache local facultatif."""
    out = {}
    for s in saisons or saisons_disponibles():
        for c in COUPES:
            chemin = os.path.join(dossier, f"{c}_{s}.txt") if dossier else None
            texte = None
            if chemin and os.path.exists(chemin) and not s.startswith(str(date.today().year - 1)) and not s.startswith(str(date.today().year)):
                texte = open(chemin, encoding="utf-8").read()                     # saison terminée : le cache suffit
            else:
                try:
                    req = urllib.request.Request(f"{BASE}/{s}/{c}.txt", headers={"User-Agent": "goalgebra"})
                    with urllib.request.urlopen(req, timeout=30) as r:
                        texte = r.read().decode("utf-8")
                    if chemin:
                        os.makedirs(dossier, exist_ok=True)
                        open(chemin, "w", encoding="utf-8").write(texte)
                except Exception:
                    if chemin and os.path.exists(chemin):
                        texte = open(chemin, encoding="utf-8").read()
            if texte:
                out[(c, s)] = texte
    return out


MOIS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
R_DATE = re.compile(r"^\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?\s*$")
R_MATCH = re.compile(r"^\s*(?:(\d{1,2}[:.]\d{2})\s+)?(.+?)\s+\(([A-Z]{3})\)\s+v\s+(.+?)\s+\(([A-Z]{3})\)\s*(.*)$")
R_SCORE = re.compile(r"(\d+)-(\d+)")


def lire(texte: str, coupe: str, saison: str) -> pd.DataFrame:
    """Une ligne par match : date, phase, équipes (nom et pays), score à 90 minutes, mi-temps, prolongation, tirs au but."""
    annee = int(saison[:4]); tour = ""; jour = None; heure = None; lignes = []
    for brut in texte.splitlines():
        if brut.startswith("▪") or brut.startswith("»"):
            tour = brut.strip("▪» ").strip(); continue
        md = R_DATE.match(brut)
        if md:
            m, d, a = MOIS[md.group(1)], int(md.group(2)), md.group(3)
            # année : explicite, sinon déduite de la saison (juillet-décembre = première année)
            annee = int(a) if a else (int(saison[:4]) if m >= 7 else int(saison[:4]) + 1)
            jour = date(annee, m, d); continue
        mm = R_MATCH.match(brut)
        if not mm or jour is None:
            continue
        if mm.group(1):
            heure = mm.group(1).replace(".", ":")
        h, hc, a, ac, reste = mm.group(2).strip(), mm.group(3), mm.group(4).strip(), mm.group(5), mm.group(6).strip()
        hg = ag = hh = ah = None; aet = pen = False
        if R_SCORE.match(reste):
            aet, pen = "a.e.t" in reste, "pen" in reste
            par = re.search(r"\(([^)]*)\)", reste)
            dans = R_SCORE.findall(par.group(1)) if par else []
            if aet:
                if dans:
                    hg, ag = map(int, dans[0])
                    if len(dans) > 1:
                        hh, ah = map(int, dans[1])
                else:
                    hg = ag = None
            else:
                hg, ag = map(int, R_SCORE.match(reste).groups())
                if dans:
                    hh, ah = map(int, dans[0])
        t = tour.lower()
        ko = any(k in t for k in CASSE["knockout"]) and "league" not in t.split(",")[0] if t else False
        lignes.append({"coupe": COUPES[coupe][0], "saison": saison, "Season": int(saison[:4]), "date": pd.Timestamp(jour),
                       "heure": heure, "tour": tour, "knockout": float(ko), "neutre": float(t.strip() == "final"),
                       "home_of": h, "home_cc": hc, "away_of": a, "away_cc": ac, "FTHome": hg, "FTAway": ag, "HTHome": hh, "HTAway": ah,
                       "aet": aet, "pen": pen, "joue": hg is not None or aet})
    return pd.DataFrame(lignes)


def charger(textes: dict) -> pd.DataFrame:
    parts = [lire(t, c, s) for (c, s), t in textes.items()]
    return pd.concat([p for p in parts if len(p)], ignore_index=True).sort_values(["date", "coupe"], kind="stable").reset_index(drop=True)


# ---------------------------------------------------------------- correspondance avec le dataset et Elo
def _cle(s: str) -> str:
    import unicodedata
    return re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()).strip()


def associer_clubs(C: pd.DataFrame, raw: pd.DataFrame) -> dict[tuple[str, str], str | None]:
    """(nom openfootball, pays) → nom du dataset, en cherchant uniquement dans les divisions du pays concerné."""
    par_div = {d: sorted(set(g.HomeTeam) | set(g.AwayTeam)) for d, g in raw[raw.MatchDate >= "2009-07-01"].groupby("Division")}
    out = {}
    for n, cc in set(zip(C.home_of, C.home_cc)) | set(zip(C.away_of, C.away_cc)):
        cands = sorted({e for d in PAYS.get(cc, []) for e in par_div.get(d, [])})
        k = _cle(n)
        k2 = re.sub(r"\b(fc|cf|afc|ac|as|sc|sk|fk|nk|gnk|bsc|ssc|ss|ogc|rc|rcd|cd|ud|sl|sv|vfb|vfl|tsg|club|de|calcio|1893|1899|1900|1904|1909|1913)\b", " ", k)
        k2 = re.sub(r"\s+", " ", k2).strip()
        if not cands:
            out[(n, cc)] = None
        elif k in ALIAS and ALIAS[k] in cands:
            out[(n, cc)] = ALIAS[k]
        elif k2 in ALIAS and ALIAS[k2] in cands:
            out[(n, cc)] = ALIAS[k2]
        else:
            out[(n, cc)] = associer(n, cands)
    return out


ELO_K, ELO_DOM, ELO_DEFAUT = 20.0, 65.0, 1500.0
_PREFIXES = r"\b(fc|cf|fk|sk|nk|gnk|hnk|bsc|ac|sc|kv|pfc|cfr|sl|afc|if|tc|ff|bk|ks|as|ssc|ss|ogc|rcd|club|royale|de|agdam|1893|1899|1900|1909|1913)\b"


def canon(nom_of: str, cc: str) -> str:
    """Identité stable d'un club d'une saison à l'autre (« GNK Dinamo Zagreb » = « Dinamo Zagreb »)."""
    k = re.sub(_PREFIXES, " ", _cle(nom_of))
    k = re.sub(r"\s+", " ", k).strip()
    return f"{k}|{cc}"


def series_elo(raw: pd.DataFrame) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Elo ClubElo de chaque club du dataset, au fil de ses matchs (dates triées, valeurs)."""
    h = raw[["MatchDate", "HomeTeam", "HomeElo"]].rename(columns={"HomeTeam": "t", "HomeElo": "e"})
    a = raw[["MatchDate", "AwayTeam", "AwayElo"]].rename(columns={"AwayTeam": "t", "AwayElo": "e"})
    L = pd.concat([h, a]).dropna().sort_values("MatchDate")
    return {t: (g.MatchDate.values, g.e.values) for t, g in L.groupby("t")}


def elo_club(series, equipe, jour, fraicheur_j=150):
    s = series.get(equipe)
    if s is None:
        return None
    i = np.searchsorted(s[0], np.datetime64(jour), side="left")
    if i == 0 or (np.datetime64(jour) - s[0][i - 1]) / np.timedelta64(1, "D") > fraicheur_j:
        return None
    return float(s[1][i - 1])


def variables(C: pd.DataFrame, raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Elo d'avant-match de chaque club (ClubElo si connu, sinon Elo estimé sur ses matchs européens) et variables du modèle."""
    corr = associer_clubs(C, raw)
    series = series_elo(raw)
    C = C.copy()
    C["home_ds"] = [corr.get((n, c)) for n, c in zip(C.home_of, C.home_cc)]
    C["away_ds"] = [corr.get((n, c)) for n, c in zip(C.away_of, C.away_cc)]
    interne, pays_elo = {}, {}
    eh, ea, esth, esta = [], [], [], []
    for r in C.itertuples():
        res = []
        for nom_of, cc, ds in ((r.home_of, r.home_cc, r.home_ds), (r.away_of, r.away_cc, r.away_ds)):
            ds = ds if isinstance(ds, str) else None
            e = elo_club(series, ds, r.date) if ds else None
            cle = ds or canon(nom_of, cc)
            if e is not None:
                interne[cle] = e; pays_elo.setdefault(cc, {})[cle] = e
                res.append((e, 0.0))
            else:
                if cle not in interne:                              # nouveau club : moyenne des clubs déjà vus de son pays
                    vus = list(pays_elo.get(cc, {}).values())
                    interne[cle] = float(np.mean(vus)) - 50 if vus else ELO_DEFAUT
                res.append((interne[cle], 1.0))
        (e1, s1), (e2, s2) = res
        eh.append(e1); ea.append(e2); esth.append(s1); esta.append(s2)
        if r.joue and r.FTHome is not None and not np.isnan(r.FTHome):     # mise à jour des Elo estimés (formule Elo classique)
            att = 1 / (1 + 10 ** (-(e1 + (0 if r.neutre else ELO_DOM) - e2) / 400))
            s = 1.0 if r.FTHome > r.FTAway else (0.5 if r.FTHome == r.FTAway else 0.0)
            ec = abs(r.FTHome - r.FTAway); mult = 1 if ec <= 1 else (1.5 if ec == 2 else (11 + ec) / 8)
            delta = ELO_K * mult * (s - att)
            for (n_, c_, d_), sg, est in (((r.home_of, r.home_cc, r.home_ds), 1, s1), ((r.away_of, r.away_cc, r.away_ds), -1, s2)):
                if est:
                    cle = d_ if isinstance(d_, str) else canon(n_, c_)
                    interne[cle] += sg * delta
                    pays_elo.setdefault(c_, {})[cle] = interne[cle]
    C["elo_h"], C["elo_a"], C["est_h"], C["est_a"] = eh, ea, esth, esta
    C["dElo"] = (C.elo_h - C.elo_a) / 100
    C["absElo"] = C.dElo.abs()
    C["dElo_n"] = C.dElo * (1 - C.neutre)                                 # l'avantage du terrain disparaît sur terrain neutre
    C["estime"] = C.est_h + C.est_a
    C["y"] = np.select([C.FTHome > C.FTAway, C.FTHome == C.FTAway], [0, 1], 2)
    C["home_key"] = [d if isinstance(d, str) else canon(n, c) for d, n, c in zip(C.home_ds, C.home_of, C.home_cc)]
    C["away_key"] = [d if isinstance(d, str) else canon(n, c) for d, n, c in zip(C.away_ds, C.away_of, C.away_cc)]
    return C, {"interne": interne, "series": series}


def elo_actuel(etat: dict, cle: str, ds: str | None, jour) -> tuple[float, bool]:
    """Elo d'un club pour un match à venir : ClubElo s'il est connu, sinon l'Elo estimé sur ses matchs européens."""
    e = elo_club(etat["series"], ds, jour) if ds else None
    if e is not None:
        return e, False
    return etat["interne"].get(cle, ELO_DEFAUT), True


def niveau_coupe(estimes: float) -> str:
    """Couverture du modèle coupes : B si au moins un des deux clubs a un Elo ClubElo, C si les deux sont estimés."""
    return "C" if estimes >= 2 else "B"


def h2h(C: pd.DataFrame, a: str, b: str, n: int = 10) -> pd.DataFrame:
    J = C[C.joue & C.FTHome.notna()]
    return J[((J.home_key == a) & (J.away_key == b)) | ((J.home_key == b) & (J.away_key == a))].tail(n)


# Testé : dElo seul (log loss 0,950) fait mieux que dElo + |dElo| + terrain neutre + phase + Elo estimé (0,956). Voir §15.
FE_COUPE = ["dElo"]


class ModeleCoupe:
    def __init__(self, cols=FE_COUPE):
        self.cols = list(cols)

    def fit(self, C: pd.DataFrame):
        T = C[C.joue & C.FTHome.notna()].copy()
        s_ref = int(T.Season.max())
        T["HTHome"], T["HTAway"] = T.HTHome.astype(float), T.HTAway.astype(float)
        self.m1x2 = Modele1X2(self.cols).fit(T, s_ref)
        self.buts = ModeleButs(self.cols).fit(T, s_ref)
        return self

    def predire(self, x: pd.DataFrame) -> dict:
        p = self.m1x2.predict(x)[0]
        lh, la = (float(z[0]) for z in self.buts.lambdas(x))
        M = grille(lh, la, self.buts.rho)
        mk = marches(M, self.buts.k_ht, lh, la)
        return {"1": p[0], "X": p[1], "2": p[2], "buts_dom": lh, "buts_ext": la, "_M": M, "scores": scores_probables(M),
                **{k: mk[k] for k in ["over15", "over25", "over35", "btts", "cs_dom", "cs_ext", "but_1re_MT"]}}


# ---------------------------------------------------------------- évaluation hors échantillon
def walk_forward(C: pd.DataFrame, premiere=2014) -> pd.DataFrame:
    """Chaque saison de coupes est prédite par un modèle entraîné sur les saisons précédentes (toutes coupes confondues)."""
    J = C[C.joue & C.FTHome.notna()].copy()
    out = []
    for s in sorted(J.Season.unique()):
        if s < premiere:
            continue
        tr, te = J[J.Season < s], J[J.Season == s]
        if len(tr) < 300 or te.empty:
            continue
        m = ModeleCoupe().fit(tr)
        P = m.m1x2.predict(te)
        out.append(te.assign(pH=P[:, 0], pD=P[:, 1], pA=P[:, 2]))
    return pd.concat(out)


def bilan(W: pd.DataFrame) -> dict:
    P = W[["pH", "pD", "pA"]].values; y = W.y.values
    base = np.tile(np.bincount(y, minlength=3) / len(y), (len(y), 1))
    elo_seul = W.assign(_p=1 / (1 + 10 ** (-(W.elo_h + ELO_DOM * (1 - W.neutre) - W.elo_a) / 400)))
    W = W.assign(pmax=P.max(1), ok=P.argmax(1) == y)
    niveaux = {}
    for k, g in W.groupby(W.estime.clip(upper=2).astype(int)):
        niveaux[f"estimés {k}"] = {"n": int(len(g)), "announced": float(g.pmax.mean()), "observed": float(g.ok.mean()),
                                   "logLoss": float(log_loss(g[["pH", "pD", "pA"]].values, g.y.values).mean())}
    return {"n": int(len(y)), "logLoss": float(log_loss(P, y).mean()), "baseline": float(log_loss(base, y).mean()),
            "accuracy": float(np.mean(P.argmax(1) == y)), "brier": float(brier(P, y).mean()), "rps": float(rps(P, y).mean()),
            "ece": float(ece(P, y)), "levels": niveaux,
            "parCoupe": {c: {"n": int(len(g)), "logLoss": float(log_loss(g[["pH", "pD", "pA"]].values, g.y.values).mean()),
                             "accuracy": float(np.mean(g[["pH", "pD", "pA"]].values.argmax(1) == g.y.values))} for c, g in W.groupby("coupe")}}


def nom_club(nom_of: str, ds: str | None) -> str:
    if isinstance(ds, str) and ds:
        return nom(ds)
    n = re.sub(r"\b(FC|CF|FK|SK|NK|GNK|BSC|AC|SC|KV|PFC|CFR)\b\.?", " ", nom_of)
    return re.sub(r"\s+", " ", n).strip() or nom_of
