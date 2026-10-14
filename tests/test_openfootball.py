from datetime import date

import pandas as pd

from footpred import openfootball as OF


def _raw():
    rows = [("E0", "2026-05-10", "Arsenal", "Man City"), ("E1", "2026-04-01", "Coventry", "Hull"), ("E0", "2026-05-11", "Nott'm Forest", "Brighton")]
    return pd.DataFrame([{"Division": d, "MatchDate": pd.Timestamp(j), "HomeTeam": h, "AwayTeam": a} for d, j, h, a in rows])


def _faux(url):
    return {"matches": [
        {"date": "2026-08-21", "time": "20:00", "team1": "Arsenal FC", "team2": "Coventry City FC", "score": {"ht": [2, 0], "ft": [3, 0]}},
        {"date": "2026-10-17", "time": "12:30", "team1": "Nottingham Forest FC", "team2": "Manchester City FC"},
        {"date": "2026-10-18", "team1": "Brighton & Hove Albion FC", "team2": "Hull City AFC", "score": {}},
        {"date": "2026-10-18", "team1": "Équipe inconnue", "team2": "Hull City AFC"}]}


def test_saison():
    assert OF.saison(date(2026, 10, 12)) == "2026-27" and OF.saison(date(2027, 3, 1)) == "2026-27"


def test_matchs_resultats_calendrier():
    ms = OF.matchs(_raw(), date(2026, 10, 12), ligues=["E0"], telecharger=_faux)
    assert [(m["home"], m["away"]) for m in ms] == [("Arsenal", "Coventry"), ("Nott'm Forest", "Man City"), ("Brighton", "Hull")]
    assert ms[0]["kickoff"] == "2026-08-21T19:00:00Z"                 # heure de Londres (BST) → UTC
    assert ms[2]["timeKnown"] is False
    R = OF.resultats(_raw(), date(2026, 10, 12), ms)
    assert len(R) == 1 and R.iloc[0].FTResult == "H" and R.iloc[0].HTHome == 2
    cal = OF.calendrier(ms, date(2026, 10, 9), date(2026, 10, 19))
    assert [m["status"] for m in cal] == ["scheduled", "scheduled"] and cal[0]["score"] is None
