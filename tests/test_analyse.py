"""Analyses affichées sur la page d'un match : intervalles, comparaison modèle / marché."""
import numpy as np
from footpred import analyse as AN


def test_intervalle_central_80():
    loi = np.array([0.05, 0.15, 0.3, 0.3, 0.15, 0.05])
    a, b = AN.intervalle(loi, 0.8)
    assert loi[a:b + 1].sum() >= 0.8 and (a, b) == (1, 4)


def test_marche_retire_la_marge_et_signale_les_desaccords():
    r = {"1": 0.50, "X": 0.27, "2": 0.23, "over25": 0.55}
    m = AN.marche(r, {"home": 1.50, "draw": 4.50, "away": 6.00, "over25": 1.70, "under25": 2.20})
    assert abs(m["home"] + m["draw"] + m["away"] - 1) < 1e-3 and m["margin"] > 0
    assert m["agreement"] == "désaccord marqué"                      # 50 % contre ≈ 64 % pour le marché
    assert AN.marche(r, {"home": 1.9}) is None                        # cotes incomplètes : pas de comparaison
    proche = AN.marche(r, {"home": 1.9, "draw": 3.5, "away": 4.1})
    assert proche["agreement"] == "accord"
