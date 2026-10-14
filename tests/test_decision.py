import numpy as np
from footpred.features import construire
from footpred.predict import Predicteur
from footpred.decision import classement, trois_decisions, palier
from footpred import statistiques as ST


def test_paliers():
    assert palier(0.9).startswith("1") and palier(0.7).startswith("2") and palier(0.55).startswith("3")
    assert palier(0.4).startswith("4") and palier(0.1).startswith("5")


def test_classement_et_coherence(raw_petit):
    pred = Predicteur(construire(raw_petit))
    r = pred.predire("Arsenal", "Chelsea")
    T = classement(r, {"Victoire Arsenal": 1.8})
    assert (np.diff(T["probabilité"].values) <= 1e-12).all()                         # trié du moins au plus risqué
    p = dict(zip(T["marché"], T["probabilité"]))
    assert abs(p["Plus de 2,5 buts"] + p["Moins de 2,5 buts"] - 1) < 1e-9          # marchés complémentaires
    assert abs(p["Arsenal ou nul (1X)"] - (r["1"] + r["X"])) < 1e-9
    v = T.set_index("marché").loc["Victoire Arsenal"]
    assert abs(v["valeur attendue"] - (v["probabilité"] * 1.8 - 1)) < 1e-9
    D = trois_decisions(T)
    assert list(D.profil) == ["prudente", "équilibrée", "audacieuse"] and D["probabilité"].iloc[0] >= D["probabilité"].iloc[2]


def test_statistiques_descriptives(raw_petit):
    d = construire(raw_petit)
    P = ST.profil(d.D, "Arsenal", 10)
    assert P["matchs"] == 10 and abs(P["victoires"] + P["nuls"] + P["défaites"] - 1) < 1e-9
    assert len(ST.confrontations(d.D, "Arsenal", "Chelsea")) >= 1
