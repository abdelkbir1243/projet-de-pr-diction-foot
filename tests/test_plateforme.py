"""Plateforme : comptes, sessions, clés d'API, quotas, API publique, import du journal (SQLite temporaire)."""
import json
import os

import pytest

pytest.importorskip("sqlalchemy"); pytest.importorskip("bcrypt"); pytest.importorskip("fastapi")


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    donnees = tmp_path / "donnees"; donnees.mkdir()
    src = os.path.join(os.path.dirname(__file__), "..", "web", "data")
    for f in os.listdir(src):
        (donnees / f).write_bytes(open(os.path.join(src, f), "rb").read())
    monkeypatch.setenv("GOALGEBRA_DATA_DIR", str(donnees))
    from plateforme import db
    db.moteur.cache_clear()
    return donnees


def test_comptes_et_force_brute(env):
    from plateforme import comptes as K
    with pytest.raises(K.ErreurCompte):
        K.creer_utilisateur("a@exemple.fr", "court1")                     # mot de passe trop faible
    u = K.creer_utilisateur("A@Exemple.fr ", "motdepasse123", "Alice")
    assert u.email == "a@exemple.fr" and u.mot_de_passe.startswith("$2")    # e-mail normalisé, mot de passe haché (bcrypt)
    with pytest.raises(K.ErreurCompte):
        K.creer_utilisateur("a@exemple.fr", "motdepasse123")              # doublon
    assert K.authentifier("a@exemple.fr", "motdepasse123").id == u.id
    for _ in range(K.ECHECS_MAX):
        with pytest.raises(K.ErreurCompte, match="incorrect"):
            K.authentifier("a@exemple.fr", "mauvais-mdp-1")
    with pytest.raises(K.ErreurCompte, match="Trop de tentatives"):
        K.authentifier("a@exemple.fr", "motdepasse123")                   # bloqué même avec le bon mot de passe
    with pytest.raises(K.ErreurCompte, match="incorrect"):
        K.authentifier("inconnu@exemple.fr", "motdepasse123")             # même message : pas d'énumération


def test_sessions_et_favoris(env):
    from plateforme import comptes as K
    u = K.creer_utilisateur("b@exemple.fr", "motdepasse123")
    jeton = K.ouvrir_session(u.id)
    assert K.utilisateur_de_session(jeton).id == u.id and K.utilisateur_de_session("faux") is None
    K.fermer_session(jeton)
    assert K.utilisateur_de_session(jeton) is None
    assert K.basculer_favori(u.id, "arsenal") and K.favoris(u.id) == ["arsenal"]
    assert not K.basculer_favori(u.id, "arsenal") and K.favoris(u.id) == []


def test_api_cles_quota(env, monkeypatch):
    from fastapi.testclient import TestClient
    from plateforme import comptes as K
    from plateforme.api import app
    u = K.creer_utilisateur("c@exemple.fr", "motdepasse123")
    cle = K.creer_cle(u.id, "test", quota_jour=5)
    c = TestClient(app)
    assert c.get("/v1/health").json()["status"] == "ok"
    assert c.get("/v1/matches").status_code == 401                         # sans clé
    assert c.get("/v1/matches", headers={"X-API-Key": "gg_faux"}).status_code == 401
    r = c.get("/v1/matches", headers={"X-API-Key": cle})
    assert r.status_code == 200 and r.json()["count"] > 0
    slug = r.json()["matches"][0]["slug"]
    assert c.get(f"/v1/matches/{slug}", headers={"X-API-Key": cle}).json()["slug"] == slug
    assert c.get("/v1/predictions/upcoming", headers={"X-API-Key": cle}).status_code == 200
    assert c.get("/v1/teams/inconnue", headers={"X-API-Key": cle}).status_code == 404
    k2 = K.creer_cle(u.id, "sélections")
    r2 = c.get("/v1/daily-selections", headers={"X-API-Key": k2})
    if r2.status_code == 200:
        j = r2.json()
        assert {"date", "generated_at", "matches_analyzed", "selections_retained", "coverage", "selections"} <= set(j)
        assert all(x["decision"] in ("selected", "cautious", "abstain") for x in j["selections"])
        assert all((x["selected_market"] is None) == (x["decision"] == "abstain") for x in j["selections"])
    assert c.get("/v1/meta", headers={"X-API-Key": cle}).status_code == 200   # 5e requête
    assert c.get("/v1/meta", headers={"X-API-Key": cle}).status_code == 429   # 6e requête : quota de 5 atteint
    k = next(x for x in K.cles(u.id) if x.prefixe == cle[:10])
    assert k.empreinte != cle and cle not in json.dumps([k.prefixe, k.empreinte])   # la clé en clair n'est jamais stockée
    K.revoquer_cle(u.id, k.id)
    assert c.get("/v1/meta", headers={"X-API-Key": cle}).status_code == 401


def test_import_journal(env):
    from plateforme.db import Prediction, session
    from plateforme.worker import importer_journal
    j = {"ok": {"madeAt": "2026-10-01T10:00:00+00:00", "kickoff": "2026-10-02T19:00:00Z", "home": "a", "away": "b", "pH": .5, "pD": .3, "pA": .2},
         "tard": {"madeAt": "2026-10-02T20:00:00+00:00", "kickoff": "2026-10-02T19:00:00Z", "home": "c", "away": "d", "pH": .5, "pD": .3, "pA": .2}}
    (env / "journal.json").write_text(json.dumps(j))
    assert importer_journal(str(env)) == 1                                  # la prédiction tardive est refusée
    j["ok"]["result"], j["ok"]["score"], j["ok"]["pH"] = "H", "2-0", .9      # le résultat est complété, la probabilité jamais réécrite
    (env / "journal.json").write_text(json.dumps(j))
    importer_journal(str(env))
    with session() as s:
        p = s.get(Prediction, "ok")
        assert p.resultat == "H" and p.p_dom == .5
