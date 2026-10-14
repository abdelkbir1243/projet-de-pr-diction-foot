"""Adaptateur football-data.org : correspondance des noms d'équipes et conversion des matchs (sans appel réseau)."""
from footpred.equipes import associer, code, slug
from footpred.live import convertir

EQ = {"E0": ["Man City", "Arsenal", "Nott'm Forest", "Wolves", "Brighton"], "SP1": ["Ath Madrid", "Betis", "Barcelona"],
      "F1": ["Paris SG", "Marseille"], "D1": ["M'gladbach", "FC Koln", "Bayern Munich"], "I1": ["Inter", "Milan"]}
TOUTES = sorted({e for v in EQ.values() for e in v})


def test_associer_noms_api():
    cas = {"Manchester City FC": "Man City", "Arsenal FC": "Arsenal", "Nottingham Forest FC": "Nott'm Forest", "Wolverhampton Wanderers FC": "Wolves",
           "Brighton & Hove Albion FC": "Brighton", "Club Atlético de Madrid": "Ath Madrid", "Real Betis Balompié": "Betis", "FC Barcelona": "Barcelona",
           "Paris Saint-Germain FC": "Paris SG", "Olympique de Marseille": "Marseille", "Borussia Mönchengladbach": "M'gladbach", "1. FC Köln": "FC Koln",
           "FC Bayern München": "Bayern Munich", "FC Internazionale Milano": "Inter", "AC Milan": "Milan",
           "RCD Espanyol de Barcelona": None, "Paris FC": None}
    for api, attendu in cas.items():
        if attendu is None:                                   # absent de la liste : ne doit pas être confondu (Barcelona, Paris SG)
            assert associer(api, TOUTES) not in ("Barcelona", "Paris SG"), api
        else:
            assert associer(api, TOUTES) == attendu, api
    assert associer("Équipe totalement inconnue", TOUTES) is None


def test_convertir_match():
    m = {"id": 123, "utcDate": "2026-10-04T15:30:00Z", "status": "IN_PLAY", "minute": 63, "matchday": 7, "competition": {"code": "PL"},
         "homeTeam": {"name": "Manchester City FC", "shortName": "Man City"}, "awayTeam": {"name": "Arsenal FC", "shortName": "Arsenal"},
         "score": {"fullTime": {"home": 1, "away": 1}, "halfTime": {"home": 0, "away": 1}}}
    c = convertir(m, EQ, TOUTES)
    assert c["id"] == "fd-123" and c["competition"] == "E0" and c["status"] == "live" and c["minute"] == 63
    assert c["home"] == "Man City" and c["away"] == "Arsenal" and c["score"] == {"home": 1, "away": 1}
    assert convertir({**m, "competition": {"code": "ELC"}}, EQ, TOUTES) is None          # compétition non suivie


def test_slug_et_code():
    assert slug("Nott'm Forest") == "nott-m-forest" and slug("Atlético Madrid") == "atletico-madrid"
    assert code("Man City") == "MCI" and code("Paris SG") == "PSG" and len(code("Werder Bremen")) == 3
