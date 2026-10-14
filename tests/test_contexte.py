"""Contexte d'avant-match : classement de la veille, enjeu de fin de saison, statut des équipes."""
import pandas as pd
from footpred import contexte as K


def test_classement_et_enjeu_fin_de_saison():
    eq = [f"E{i}" for i in range(20)]
    t = K.Table.vide(eq)
    for i, e in enumerate(eq):                     # 34 journées jouées : points décroissants avec le rang
        t.pts[e], t.j[e] = 80 - 3 * i, 34
    assert t.ordre()[0] == "E0"
    tete = K.enjeu(t, "E0", 20, "E0")              # leader avec 3 points d'avance, 4 matchs restants
    assert tete["titre"] == 1 and tete["restants"] == 4
    milieu = K.enjeu(t, "E10", 20, "E0")           # 10 points sur la zone rouge, loin de l'Europe
    assert milieu["sans_enjeu"] == 1
    bas = K.enjeu(t, "E16", 20, "E0")              # juste au-dessus de la zone de relégation
    assert bas["maintien"] == 1


def test_pas_d_enjeu_en_debut_de_saison():
    t = K.Table.vide(["A", "B"]); t.ajouter("A", "B", 2, 0)
    e = K.enjeu(t, "A", 20, "E0")
    assert e["titre"] == e["maintien"] == e["sans_enjeu"] == 0


def test_statut_promu_et_champion():
    D = pd.DataFrame({"Division": ["E0"] * 4, "Season": [2020, 2020, 2021, 2021], "HomeTeam": ["A", "B", "A", "C"],
                      "AwayTeam": ["B", "A", "C", "A"], "FTHome": [3, 0, 1, 1], "FTAway": [0, 1, 1, 1]})
    s = K.statut_saison(D)
    assert s[("E0", 2021, "A")]["champion"] == 1 and s[("E0", 2021, "C")]["promu"] == 1 and s[("E0", 2021, "C")]["premiere"] == 1
    assert s[("E0", 2021, "A")]["promu"] == 0
