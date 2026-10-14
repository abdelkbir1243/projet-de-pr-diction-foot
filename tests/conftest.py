import os, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from footpred.data import charger_matchs


@pytest.fixture(scope="session")
def raw_petit():
    """Deux saisons seulement (2016/17-2017/18) pour des tests rapides."""
    raw = charger_matchs()
    return raw[(raw.MatchDate >= "2016-07-01") & (raw.MatchDate < "2018-07-01")].reset_index(drop=True)
