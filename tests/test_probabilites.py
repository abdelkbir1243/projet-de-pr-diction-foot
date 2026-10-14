import numpy as np
import pandas as pd
from footpred.models import grille, tau
from footpred.markets import shin, marches
from footpred.ratings import GasRatings
from footpred.evaluation import rps, log_loss


def test_grille_somme_a_un():
    for lh, la, r in [(1.5, 1.1, -0.05), (0.3, 3.2, 0.0), (2.8, 0.4, -0.1)]:
        M = grille(lh, la, r)
        assert abs(M.sum() - 1) < 1e-12 and (M >= 0).all()


def test_tau_neutre_si_rho_nul():
    assert np.allclose(tau(np.array([0, 1, 2]), np.array([0, 1, 0]), 1.3, 1.1, 0.0), 1)


def test_marches_coherents():
    M = grille(1.6, 1.2, -0.05); m = marches(M, 0.44, 1.6, 1.2)
    assert abs(m["1 (grille)"] + m["X (grille)"] + m["2 (grille)"] - 1) < 1e-12
    assert m["over15"] > m["over25"] > m["over35"]


def test_shin_retire_la_marge():
    p, marge = shin([1.45, 4.6, 6.5])
    assert abs(p.sum() - 1) < 1e-4 and marge > 0


def test_gas_attaque_augmente_quand_on_marque():
    d = pd.DataFrame({"HomeTeam": ["A"] * 20, "AwayTeam": ["B"] * 20, "Division": ["X"] * 20, "FTHome": [4.] * 20, "FTAway": [0.] * 20})
    g = GasRatings(); out = g.calculer(d)
    assert out[-1, 0] > out[0, 0] and out[-1, 1] < out[0, 1]
    assert g.att["A"] > 0 and g.dfn["B"] < 0


def test_metriques_valeurs_connues():
    P = np.array([[1 / 3, 1 / 3, 1 / 3]]); y = np.array([0])
    assert abs(log_loss(P, y)[0] - np.log(3)) < 1e-12
    assert abs(rps(np.array([[1., 0, 0]]), y)[0]) < 1e-12
