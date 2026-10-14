"""Honnêteté du journal : aucune prédiction enregistrée au coup d'envoi ou après."""
import json
import os
from datetime import datetime, timezone

from footpred.web import figeable, nettoyer_journal

T = lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
M = {"id": "x", "status": "scheduled", "kickoff": "2026-10-12T19:00:00Z"}


def test_figeable_seulement_avant_le_coup_d_envoi():
    assert figeable(M, {"home": .5}, {}, T("2026-10-12T18:59:00"), "fixtures")
    assert not figeable(M, {"home": .5}, {}, T("2026-10-12T19:00:00"), "fixtures")      # pile au coup d'envoi
    assert not figeable(M, {"home": .5}, {}, T("2026-10-13T10:00:00"), "live")          # match passé, score inconnu
    assert not figeable(M, {"home": .5}, {}, T("2026-10-12T10:00:00"), "replay")        # pas de journal en rejeu
    assert not figeable(M, {"home": .5}, {"x": {}}, T("2026-10-12T10:00:00"), "live")   # déjà figée : jamais réécrite
    assert not figeable({**M, "status": "finished"}, {"home": .5}, {}, T("2026-10-12T10:00:00"), "live")


def test_nettoyage_des_entrees_invalides():
    j = {"ok": {"madeAt": "2026-10-12T10:00:00+00:00", "kickoff": "2026-10-12T19:00:00Z"},
         "apres": {"madeAt": "2026-10-12T21:00:00+00:00", "kickoff": "2026-10-12T19:00:00Z"},
         "pile": {"madeAt": "2026-10-12T19:00:00+00:00", "kickoff": "2026-10-12T19:00:00Z"}, "incomplete": {"kickoff": "2026-10-12T19:00:00Z"}}
    assert nettoyer_journal(j) == 3 and list(j) == ["ok"]


def test_journal_publie_valide():
    f = os.path.join(os.path.dirname(__file__), "..", "web", "data", "journal.json")
    if not os.path.exists(f):
        return
    j = json.load(open(f, encoding="utf-8"))
    mauvaises = [k for k, v in j.items() if datetime.fromisoformat(v["madeAt"]) >= datetime.fromisoformat(v["kickoff"].replace("Z", "+00:00"))]
    assert not mauvaises, f"{len(mauvaises)} prédictions enregistrées après le coup d'envoi"


def test_marches_sans_match_commence():
    f = os.path.join(os.path.dirname(__file__), "..", "web", "data", "markets.json")
    m = os.path.join(os.path.dirname(__file__), "..", "web", "data", "matches.json")
    if not (os.path.exists(f) and os.path.exists(m)):
        return
    meta = json.load(open(os.path.join(os.path.dirname(f), "meta.json"), encoding="utf-8"))
    gen = datetime.fromisoformat(meta["generatedAt"])
    commences = {x["slug"] for x in json.load(open(m, encoding="utf-8"))
                 if datetime.fromisoformat(x["kickoff"].replace("Z", "+00:00")) <= gen and meta.get("mode") != "replay"}
    assert not [r for r in json.load(open(f, encoding="utf-8"))["rows"] if r["match"] in commences]


def test_horaire_non_fiable_jamais_fige():
    assert not figeable({**M, "timeKnown": False}, {"home": .5}, {}, T("2026-10-12T10:00:00"), "fixtures")


def test_etats_des_matchs():
    from footpred.web import etat
    n = T("2026-10-12T20:00:00")
    base = {"status": "scheduled", "kickoff": "2026-10-12T21:00:00Z", "prediction": {"home": .5}, "timeKnown": True}
    assert etat(base, n) == "prematch_open"
    assert etat({**base, "prediction": None}, n) == "scheduled"
    assert etat({**base, "timeKnown": False}, n) == "scheduled"
    assert etat({**base, "kickoff": "2026-10-12T19:00:00Z"}, n) == "live"              # commencé, sans flux en direct
    assert etat({**base, "kickoff": "2026-10-12T17:00:00Z"}, n) == "awaiting_result"   # > 2 h 15 sans score
    assert etat({**base, "status": "halftime"}, n) == "live"
    for s in ("finished", "postponed", "cancelled"):
        assert etat({**base, "status": s}, n) == s
