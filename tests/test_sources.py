"""Adaptateurs des sources réelles (formats football-data.co.uk) et fusion avec l'historique, testés hors ligne."""
import numpy as np
import pandas as pd
from footpred import sources as S

SAISON = """Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,HTHG,HTAG,HTR,Referee,HS,AS,HST,AST,HF,AF,HC,AC,HY,AY,HR,AR,B365H,B365D,B365A,AvgH,AvgD,AvgA,MaxH,MaxD,MaxA,Avg>2.5,Avg<2.5
E0,13/09/2026,15:00,Arsenal,Chelsea,2,1,H,1,0,H,M Oliver,15,9,6,3,10,12,7,4,1,2,0,0,1.80,3.80,4.50,1.78,3.75,4.40,1.85,3.90,4.70,1.70,2.15
E0,14/09/2026,20:00,Everton,Fulham,,,,,,,,,,,,,,,,,,,,2.40,3.20,3.00,2.35,3.20,3.05,2.50,3.30,3.10,2.10,1.75
"""
FIXTURES = """Div,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A,AvgH,AvgD,AvgA,Avg>2.5,Avg<2.5
E0,20/09/2026,12:30,Liverpool,Arsenal,2.10,3.60,3.40,2.05,3.55,3.45,1.62,2.30
SC0,20/09/2026,15:00,Celtic,Rangers,1.90,3.80,3.80,1.88,3.70,3.75,1.60,2.35
F1,20/01/2027,21:00,Paris SG,Lyon,1.40,5.00,7.00,,,,,
"""


def test_resultats_seulement_les_matchs_joues():
    r = S.lire_resultats_fduk(SAISON)
    assert len(r) == 1
    m = r.iloc[0]
    assert m.Division == "E0" and m.FTHome == 2 and m.HomeCorners == 7 and m.OddHome == 1.78
    assert m.MatchDate == pd.Timestamp("2026-09-13")


def test_calendrier_heure_de_londres_en_utc_et_cotes():
    cal = S.lire_calendrier_fduk(FIXTURES)
    assert [c["competition"] for c in cal] == ["E0", "F1"]                       # ligue écossaise ignorée
    assert cal[0]["kickoff"] == "2026-09-20T11:30:00Z"                           # heure d'été : UTC+1
    assert cal[1]["kickoff"] == "2027-01-20T21:00:00Z"                           # heure d'hiver : UTC+0
    assert cal[0]["odds"]["home"] == 2.05 and cal[0]["odds"]["over25"] == 1.62
    assert cal[1]["odds"]["home"] == 1.40                                        # repli sur Bet365 sans moyenne


def test_code_saison():
    assert S.code_saison(pd.Timestamp("2026-09-01").date()) == "2627"
    assert S.code_saison(pd.Timestamp("2027-03-01").date()) == "2627"


def test_fusion_sans_doublon_et_elo_propage():
    raw = pd.DataFrame({"Division": ["E0", "E0"], "MatchDate": pd.to_datetime(["2026-09-01", "2026-09-06"]), "HomeTeam": ["Arsenal", "Chelsea"],
                        "AwayTeam": ["Chelsea", "Arsenal"], "FTHome": [1, 0], "FTAway": [0, 0], "HomeElo": [1900.0, 1850.0], "AwayElo": [1850.0, 1905.0],
                        "Season": [2026, 2026]})
    rec = S.lire_resultats_fduk(SAISON)
    out, n = S.fusionner(raw, pd.concat([rec, rec]).drop_duplicates())
    assert n == 1 and len(out) == 3
    der = out.iloc[-1]
    assert abs(der.HomeElo - 1905) < 15 and abs(der.AwayElo - 1850) < 15        # dernier Elo connu + mise à jour du nul
    out2, n2 = S.fusionner(out, rec)
    assert n2 == 0                                                               # deuxième passage : rien de nouveau


def test_propagation_elo_conserve_la_somme():
    raw = pd.DataFrame({"Division": ["E0"] * 3, "MatchDate": pd.to_datetime(["2026-08-01", "2026-08-08", "2026-08-15"]),
                        "HomeTeam": ["A", "B", "A"], "AwayTeam": ["B", "A", "B"], "FTHome": [1, 2, 3], "FTAway": [0, 2, 0],
                        "HomeElo": [1500.0, np.nan, np.nan], "AwayElo": [1500.0, np.nan, np.nan]})
    out = S.propager_elo(raw)
    assert out.HomeElo.notna().all()
    assert abs(out.HomeElo.iloc[2] + out.AwayElo.iloc[2] - 3000) < 1e-9


def test_ordre_des_sources_variable_vide(monkeypatch):
    monkeypatch.setenv("GOALGEBRA_SOURCES", "")
    assert S.ordre_sources() == ["footballdata_org", "football_data_co_uk", "openfootball"]
    monkeypatch.setenv("GOALGEBRA_SOURCES", "football_data_co_uk")
    assert S.ordre_sources() == ["football_data_co_uk", "openfootball"]          # le secours GitHub reste en dernier
