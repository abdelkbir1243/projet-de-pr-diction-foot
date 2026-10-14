"""Degré de confiance : intervalles, niveaux, calibration, sommes de probabilités d'une journée."""
import numpy as np
import pandas as pd
from footpred import confiance as CF


def test_wilson_contient_la_proportion_et_se_resserre():
    a, b = CF.wilson(60, 100)
    c, d = CF.wilson(600, 1000)
    assert a < 0.6 < b and c < 0.6 < d and (d - c) < (b - a)


def test_niveaux():
    assert CF.niveau(0.02, 20) == "A"
    assert CF.niveau(0.02, 2) == "B"            # début de saison
    assert CF.niveau(0.07, 20) == "B"
    assert CF.niveau(0.12, 20) == "C"
    assert CF.niveau(np.nan, 20) == "A"         # sans cotes : seul le début de saison compte


def test_calibration_et_recherche():
    rng = np.random.default_rng(0)
    p = rng.uniform(0.5, 0.9, 20000)
    A = pd.DataFrame({"marché": "Plus de 1,5 buts", "famille": "Buts", "p": p, "réalisé": rng.random(20000) < p})
    cal = CF.calibration_marches(A)
    c = CF.chercher(cal, "Plus de 1,5 buts", 0.72)
    assert c and 0.70 <= c["announced"] < 0.75 and abs(c["observed"] - c["announced"]) < 0.03 and c["lo"] < c["observed"] < c["hi"] and c["n"] > 1000
    assert CF.chercher(cal, "Plus de 1,5 buts", 0.2) is None      # classe sans données


def test_journee_somme_des_probabilites():
    loi = CF.poisson_binomiale([0.5, 0.5, 0.5, 0.5])
    assert np.isclose(loi.sum(), 1) and np.isclose((np.arange(5) * loi).sum(), 2)
    tot = CF.convoluer([np.array([0.5, 0.5]), np.array([0.5, 0.5])])
    assert np.allclose(tot, [0.25, 0.5, 0.25])
    a, b = CF.intervalle(loi)
    assert a <= 2 <= b
