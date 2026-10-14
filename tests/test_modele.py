import numpy as np
from footpred.features import construire
from footpred.predict import Predicteur


def test_prediction_bout_en_bout(raw_petit):
    pred = Predicteur(construire(raw_petit))
    r = pred.simulation("Arsenal", "Chelsea", afficher=False)
    assert abs(r["1"] + r["X"] + r["2"] - 1) < 1e-9
    assert 0 < r["buts_dom"] < 5 and 0 < r["buts_ext"] < 5
    assert 0 < r["over25"] < 1 and 0 < r["btts"] < 1


def test_equipe_inconnue_propose_des_noms(raw_petit):
    pred = Predicteur(construire(raw_petit))
    try:
        pred.predire("Arsenall", "Chelsea"); assert False
    except ValueError as e:
        assert "Arsenal" in str(e)
