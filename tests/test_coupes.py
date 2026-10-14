"""Coupes d'Europe : lecture du format openfootball (années, prolongations), identité des clubs, Elo estimé."""
import pandas as pd
from footpred import coupes as K

TEXTE = """= UEFA Champions League 2015/16

▪ Group A
  Tue Sep 15 2015
    20:45  Real Madrid (ESP)       v Shakhtar Donetsk (UKR)   4-0 (1-0)
  Tue Dec 8
    20:45  Shakhtar Donetsk (UKR)  v Malmö FF (SWE)           4-0 (1-0)

▪ Group B
  Tue Sep 15
    20:45  PSV Eindhoven (NED)     v Manchester United (ENG)  2-1 (1-1)

▪ Final
  Sat May 28
    20:45  Real Madrid (ESP)       v Atlético Madrid (ESP)    5-3 pen. 1-1 a.e.t. (1-1, 1-0)
           Bayern München (GER)    v Juventus (ITA)           4-2 a.e.t. (2-2, 0-2)
           Arsenal FC (ENG)        v Chelsea FC (ENG)
"""


def test_lecture_dates_et_scores():
    C = K.lire(TEXTE, "cl", "2015-16")
    assert len(C) == 6
    assert list(C.date.dt.year) == [2015, 2015, 2015, 2016, 2016, 2016]           # pas d'année « 2016 » pour le groupe B
    finale = C.iloc[3]
    assert finale.neutre == 1 and finale.knockout == 1 and finale.aet and finale.pen
    assert (finale.FTHome, finale.FTAway, finale.HTHome, finale.HTAway) == (1, 1, 1, 0)   # score à 90 minutes, pas celui des tirs au but
    assert (C.iloc[4].FTHome, C.iloc[4].FTAway) == (2, 2)
    assert not C.iloc[5].joue and pd.isna(C.iloc[5].FTHome)                         # match à venir
    assert C.iloc[0].knockout == 0


def test_identite_stable_des_clubs():
    assert K.canon("GNK Dinamo Zagreb", "CRO") == K.canon("Dinamo Zagreb", "CRO")
    assert K.canon("Qarabağ Ağdam FK", "AZE") == K.canon("Qarabağ FK", "AZE")
    assert K.canon("Dinamo Zagreb", "CRO") != K.canon("Dinamo Zagreb", "ROU")


def test_elo_estime_pour_les_clubs_inconnus():
    C = K.lire(TEXTE, "cl", "2015-16")
    raw = pd.DataFrame({"Division": ["SP1"], "MatchDate": pd.to_datetime(["2015-09-01"]), "HomeTeam": ["Real Madrid"], "AwayTeam": ["Getafe"],
                        "HomeElo": [1950.0], "AwayElo": [1600.0]})
    V, etat = K.variables(C, raw)
    r0 = V.iloc[0]
    assert r0.home_ds == "Real Madrid" and r0.elo_h == 1950 and r0.est_h == 0
    assert r0.est_a == 1 and r0.elo_a == K.ELO_DEFAUT                             # Shakhtar : aucun Elo connu
    assert V.iloc[1].elo_h < K.ELO_DEFAUT                                        # après la défaite 4-0 : son Elo estimé a baissé
    assert etat["interne"][K.canon("Shakhtar Donetsk", "UKR")] > V.iloc[1].elo_h  # puis remonte après sa victoire 4-0
