"""Moteur de sélection : cohérence des marchés, décisions, abstention, figement avant le coup d'envoi, fenêtres temporelles."""
import json
import os
from datetime import datetime, timezone

import numpy as np
import pytest

from footpred import selection as S
from footpred.models import grille

M = grille(1.7, 1.0, -0.05)


def test_distribution_conjointe_coherente():
    p = np.array([0.55, 0.25, 0.20])
    Ma = S.ajuster_grille(M, p)
    k = S.probas_marches(Ma)
    assert abs(Ma.sum() - 1) < 1e-9
    assert np.allclose([k["home"], k["draw"], k["away"]], p)
    assert abs(k["dc_1x"] - (k["home"] + k["draw"])) < 1e-12 and abs(k["dc_12"] - (1 - k["draw"])) < 1e-12
    assert abs(k["over25"] + k["under25"] - 1) < 1e-12 and abs(k["btts_yes"] + k["btts_no"] - 1) < 1e-12
    assert abs(k["dnb_home"] - k["home"] / (k["home"] + k["away"])) < 1e-12
    assert k["over05"] >= k["over15"] >= k["over25"] and k["under25"] <= k["under35"]
    assert k["btts_yes"] <= min(k["home_scores"], k["away_scores"])                     # P(A∩B) ≤ min(P(A), P(B))
    # la forme des scores à l'intérieur de chaque issue est conservée
    hw, _, _ = S.regions()
    assert np.allclose(Ma[hw] / Ma[hw].sum(), M[hw] / M[hw].sum())


def test_issues_observees():
    assert S.issue("dnb_home", 1, 1) is None and S.issue("dnb_home", 2, 1) == 1
    assert S.issue("over25", 2, 1) == 1 and S.issue("under25", 1, 1) == 1 and S.issue("btts_no", 3, 0) == 1


SEUILS = {"p_bas_min": 0.79, "info_min": 0.02, "desaccord_max": 1.0, "p_prudente_min": 0.69}


def cand(cle, p, p_bas, ref):
    return {"cle": cle, "p": p, "p_bas": p_bas, "ref": ref, "info": float(S.kl_bits(p, ref))}


def test_decisions_et_abstention():
    fort = cand("home_scores", 0.86, 0.84, 0.70)
    trivial = cand("over05", 0.93, 0.92, 0.93)
    moyen = cand("dc_x2", 0.74, 0.70, 0.55)
    assert S.decider([fort, trivial], SEUILS, 0.05, True)["decision"] == "retenue"
    assert S.decider([fort, trivial], SEUILS, 0.05, True)["choix"]["cle"] == "home_scores"     # pas la plus probable, la plus informative
    plus = cand("away_scores", 0.88, 0.86, 0.62)
    assert S.decider([fort, plus, trivial], SEUILS, 0.05, True, "probable")["choix"]["cle"] == "away_scores"   # p max parmi les informatives
    assert S.decider([fort, plus, trivial], SEUILS, 0.05, True)["choix"]["cle"] == "away_scores"               # écart à la référence maximal
    assert S.decider([moyen, trivial], SEUILS, 0.05, True)["decision"] == "prudente"
    r = S.decider([trivial], SEUILS, 0.05, True)                                               # aucune information : abstention
    assert r["decision"] == "abstention" and r["choix"] is None
    r = S.decider([fort], SEUILS, 0.05, False)                                                 # qualité insuffisante : jamais retenue ni prudente
    assert r["decision"] == "abstention" and "qualité" in r["raisons"][0]
    assert S.decider([fort], {**SEUILS, "desaccord_max": 0.1}, 0.3, True)["decision"] == "prudente"


def test_borne_basse_et_determinisme():
    mm = S.MetaModele(); mm.beta = np.r_[0.0, 1.0, np.zeros(len(S.NOMS_META) - 2)]; mm.cov = np.eye(len(S.NOMS_META)) * 1e-4
    Z = S.variables_meta([0.8, 0.8], ["Buts", "Buts"], [0.1, 0.1], [0.9, 0.9], [1, 1], [0, 0])
    p1, b1 = mm.predict(Z, [0.0, 0.5])
    p2, b2 = mm.predict(Z, [0.0, 0.5])
    assert np.allclose(p1, 0.8) and b1[0] < p1[0] and b1[1] < b1[0]          # plus de dispersion entre modèles → borne plus basse
    assert np.array_equal(b1, b2)


def test_reference_sans_cotes():
    assert S.probas_marche_reference(None, None) == {}                          # pas de cote : fréquence historique, pas d'EV
    r = S.probas_marche_reference(np.array([0.5, 0.3, 0.2]), 0.55)
    assert abs(r["dc_1x"] - 0.8) < 1e-12 and abs(r["under25"] - 0.45) < 1e-12


def test_selection_figee_avant_coup_envoi():
    from footpred.web import figer_selection
    sel = {"decision": "retenue", "choix": {"cle": "home", "marche": "x", "famille": "Résultat", "p": .8, "p_bas": .79, "ref": .6},
           "plus_probable": {"cle": "home", "marche": "x", "famille": "Résultat", "p": .8, "p_bas": .79, "ref": .6}, "confiance": .79,
           "qualite": 100, "desaccord": .05, "entropie": .7, "raisons": [], "createdAt": "t", "modelVersion": "v", "dataVersion": "d", "selectionId": "s"}
    m = {"id": "m1", "kickoff": "2026-10-17T15:00:00Z"}
    avant, apres = datetime(2026, 10, 17, 14, tzinfo=timezone.utc), datetime(2026, 10, 17, 15, 1, tzinfo=timezone.utc)
    j = {"m1": {}}
    assert not figer_selection(j, m, sel, apres, "fixtures") and "selection" not in j["m1"]       # après le coup d'envoi : refusée
    assert figer_selection(j, m, sel, avant, "fixtures")
    autre = {**sel, "decision": "abstention"}
    assert not figer_selection(j, m, autre, avant, "fixtures") and j["m1"]["selection"]["decision"] == "retenue"   # jamais réécrite
    assert not figer_selection({"m1": {}}, m, {**sel, "predictionType": "live"}, avant, "fixtures")              # le live ne remplace rien
    assert not figer_selection({"m1": {}}, m, sel, avant, "replay")


def test_fenetres_temporelles_disjointes():
    from footpred.banc import FENETRE_A, FENETRE_B, FENETRE_T
    assert max(FENETRE_A) < min(FENETRE_B) and max(FENETRE_B) < min(FENETRE_T)
    f = os.path.join(os.path.dirname(__file__), "..", "footpred", "artefacts", "selection.json")
    if os.path.exists(f):
        a = json.load(open(f, encoding="utf-8"))
        assert a["fenetres"]["T"] == FENETRE_T and set(a["fenetres"]["B"]).isdisjoint(a["fenetres"]["T"])
        assert set(a["seuils"]) == set(SEUILS)


def test_selections_publiees_avant_match():
    f = os.path.join(os.path.dirname(__file__), "..", "web", "data", "selections.json")
    j = os.path.join(os.path.dirname(__file__), "..", "web", "data", "journal.json")
    if os.path.exists(j):
        for v in json.load(open(j, encoding="utf-8")).values():
            s = v.get("selection")
            if s:
                assert datetime.fromisoformat(s["createdAt"]) < datetime.fromisoformat(v["kickoff"].replace("Z", "+00:00"))
    if os.path.exists(f):
        for jour in json.load(open(f, encoding="utf-8")).values():
            n = jour["retained"] + jour["prudent"] + jour["abstentions"]
            assert n == jour["matches"] == len(jour["items"])
            for it in jour["items"]:
                assert (it["choix"] is None) == (it["decision"] == "abstention")
