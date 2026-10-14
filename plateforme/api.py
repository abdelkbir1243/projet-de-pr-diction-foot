"""API publique Goalgebra (FastAPI). Documentation interactive : /docs ; schéma : /openapi.json.

Authentification : en-tête `X-API-Key: gg_…` (clé créée depuis la page « Mon compte » de l'application).
Limites : quota quotidien par clé (1 000 par défaut) et 60 requêtes par minute par clé (429 au-delà).
Les données sont celles publiées par le worker (GOALGEBRA_DATA_DIR) : probabilités statistiques, jamais des conseils de pari.

    uvicorn plateforme.api:app --host 0.0.0.0 --port 8000
"""
import json
import os
import threading
import time
from collections import defaultdict, deque
from datetime import date, datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from sqlalchemy import select

from .comptes import consommer
from .db import ExecutionPipeline, Prediction, session
from .worker import dossier_donnees

from footpred.version import MODELE, __version__ as VERSION_PROJET  # noqa: E402
VERSION = "1.1"                 # version de l'API (contrat des routes)
app = FastAPI(title="Goalgebra API", version=VERSION,
              description="Probabilités et statistiques d'avant-match pour les 5 grands championnats et les coupes d'Europe. "
                          "Projet académique : probabilités statistiques, jamais des résultats garantis ni des conseils de pari.",
              docs_url="/docs", redoc_url=None)
app.add_middleware(GZipMiddleware, minimum_size=1000)
ENTETE = APIKeyHeader(name="X-API-Key", auto_error=False)
PAR_MINUTE = int(os.environ.get("API_LIMITE_MINUTE", "60"))
_fenetres: dict[int, deque] = defaultdict(deque)
_verrou = threading.Lock()


@app.middleware("http")
async def entetes_securite(request: Request, call_next):
    r = await call_next(request)
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["Referrer-Policy"] = "no-referrer"
    r.headers["Cache-Control"] = "no-store" if request.url.path != "/v1/health" else "max-age=30"
    return r


# ---------------------------------------------------------------- données (relues seulement si le fichier a changé)
_cache: dict[str, tuple[float, object]] = {}


def lire(nom: str, defaut=None):
    f = os.path.join(dossier_donnees(), nom)
    try:
        t = os.path.getmtime(f)
    except OSError:
        return defaut
    c = _cache.get(f)
    if c and c[0] == t:
        return c[1]
    with open(f, encoding="utf-8") as fh:
        obj = json.load(fh)
    _cache[f] = (t, obj)
    return obj


# ---------------------------------------------------------------- authentification et limites
def cle_valide(cle: str | None = Security(ENTETE)):
    k, raison = consommer(cle or "")
    if not k:
        code = 429 if "quota" in raison else 401
        raise HTTPException(code, detail=raison, headers={"WWW-Authenticate": "ApiKey"} if code == 401 else None)
    maintenant = time.monotonic()
    with _verrou:
        w = _fenetres[k.id]
        while w and maintenant - w[0] > 60:
            w.popleft()
        if len(w) >= PAR_MINUTE:
            raise HTTPException(429, detail=f"limite de {PAR_MINUTE} requêtes par minute atteinte", headers={"Retry-After": "60"})
        w.append(maintenant)
    return k


def _resume(m: dict) -> dict:
    p = m.get("prediction") or None
    return {"slug": m["slug"], "competition": m["competition"], "kickoff": m["kickoff"], "status": m["status"],
            "awaitingResult": m.get("awaitingResult", False), "home": m["home"], "away": m["away"], "homeName": m["homeName"],
            "awayName": m["awayName"], "score": m.get("score"),
            "prediction": None if not p else {k: p.get(k) for k in ("home", "draw", "away", "xg", "likelyScore", "over25", "btts", "source", "frozenAt")}
            | {"confidenceLevel": (p.get("trust") or {}).get("level")}}


# ---------------------------------------------------------------- routes
@app.get("/v1/health", tags=["service"], summary="État du service (sans clé)")
def sante():
    meta = lire("meta.json", {}) or {}
    with session() as s:
        run = s.scalar(select(ExecutionPipeline).order_by(ExecutionPipeline.debut.desc()).limit(1))
    return {"status": "ok" if meta else "no-data", "version": VERSION, "project": VERSION_PROJET, "model": meta.get("model", MODELE), "generatedAt": meta.get("generatedAt"), "mode": meta.get("mode"),
            "freshness": meta.get("freshness"), "lastRun": None if not run else {"status": run.statut, "start": run.debut.isoformat()}}


@app.get("/v1/meta", tags=["données"])
def meta(_=Depends(cle_valide)):
    return lire("meta.json", {})


@app.get("/v1/competitions", tags=["données"])
def competitions(_=Depends(cle_valide)):
    return lire("competitions.json", [])


@app.get("/v1/matches", tags=["données"], summary="Matchs (filtres : date, compétition, équipe, statut)")
def matchs(jour: date | None = Query(None, alias="date", description="AAAA-MM-JJ (UTC)"), competition: str | None = None,
           team: str | None = None, status: str | None = Query(None, pattern="^(scheduled|live|halftime|finished|postponed|cancelled)$"),
           limit: int = Query(200, ge=1, le=500), _=Depends(cle_valide)):
    out = []
    for m in lire("matches.json", []):
        if jour and m["kickoff"][:10] != jour.isoformat():
            continue
        if competition and m["competition"] != competition:
            continue
        if team and team not in (m["home"], m["away"]):
            continue
        if status and m["status"] != status:
            continue
        out.append(_resume(m))
    return {"count": len(out[:limit]), "matches": out[:limit]}


@app.get("/v1/matches/{slug}", tags=["données"], summary="Fiche complète d'un match (prédiction, marchés, contexte, H2H)")
def match(slug: str, _=Depends(cle_valide)):
    m = next((x for x in lire("matches.json", []) if x["slug"] == slug), None)
    if not m:
        raise HTTPException(404, "match inconnu")
    return m


@app.get("/v1/predictions/upcoming", tags=["prédictions"], summary="Prédictions des matchs à venir (avant le coup d'envoi)")
def a_venir(competition: str | None = None, _=Depends(cle_valide)):
    now = datetime.now(timezone.utc)
    out = [_resume(m) for m in lire("matches.json", []) if m.get("prediction") and m["status"] == "scheduled" and not m.get("started")
           and datetime.fromisoformat(m["kickoff"].replace("Z", "+00:00")) > now and (not competition or m["competition"] == competition)]
    return {"count": len(out), "predictions": out}


@app.get("/v1/predictions/journal", tags=["prédictions"], summary="Journal public : prédictions figées avant le coup d'envoi et résultats")
def journal(depuis: date | None = None, limit: int = Query(200, ge=1, le=1000), _=Depends(cle_valide)):
    with session() as s:
        q = select(Prediction).order_by(Prediction.coup_envoi.desc()).limit(limit)
        if depuis:
            q = q.where(Prediction.coup_envoi >= datetime.combine(depuis, datetime.min.time(), tzinfo=timezone.utc))
        rows = list(s.scalars(q))
    return {"count": len(rows), "predictions": [{"id": p.id, "madeAt": p.faite_le.isoformat(), "kickoff": p.coup_envoi.isoformat(), "home": p.domicile,
                                                 "away": p.exterieur, "pH": p.p_dom, "pD": p.p_nul, "pA": p.p_ext, "model": p.modele,
                                                 "result": p.resultat, "score": p.score} for p in rows]}


NIVEAU = {"retenue": "high", "prudente": "moderate", "abstention": "low"}
DECISION_API = {"retenue": "selected", "prudente": "cautious", "abstention": "abstain"}


@app.get("/v1/daily-selections", tags=["prédictions"], summary="Sélection du jour : sélection retenue, analyse prudente ou abstention par match")
def selections_du_jour(jour: date | None = Query(None, alias="date", description="AAAA-MM-JJ (Europe/Paris) ; par défaut le prochain jour publié"),
                       _=Depends(cle_valide)):
    sels = lire("selections.json", {}) or {}
    if not sels:
        raise HTTPException(404, "aucune sélection publiée")
    cle = jour.isoformat() if jour else next((j for j in sorted(sels) if j >= datetime.now(timezone.utc).date().isoformat()), sorted(sels)[-1])
    S = sels.get(cle)
    if not S:
        raise HTTPException(404, "aucune sélection pour cette date")
    out = []
    for it in S["items"]:
        c = it.get("choix") or {}
        out.append({"match_id": it["match"], "competition": it["competition"], "home_team": it["homeName"], "away_team": it["awayName"],
                    "kickoff_at": it["kickoff"], "decision": DECISION_API[it["decision"]], "selected_market": c.get("cle"),
                    "selected_outcome": c.get("marche"), "probability": c.get("p"), "probability_lower_bound": c.get("p_bas"),
                    "reference_probability": c.get("ref"), "reference_source": c.get("ref_source"), "edge": c.get("ecart"),
                    "expected_value": c.get("ev"), "conservative_expected_value": c.get("ev_prudente"),
                    "confidence_level": NIVEAU[it["decision"]], "data_quality_score": round((it.get("qualite") or 0) / 100, 2),
                    "model_disagreement": it.get("desaccord"), "entropy": it.get("entropie"), "explanation": it.get("raisons") or [],
                    "created_at": it.get("createdAt"), "model_version": it.get("modelVersion"), "data_version": it.get("dataVersion"),
                    "selection_id": it.get("selectionId")})
    return {"date": cle, "generated_at": S["generatedAt"], "matches_analyzed": S["matches"], "selections_retained": S["retained"],
            "cautious": S["prudent"], "abstentions": S["abstentions"], "coverage": S["coverage"], "freshness": S.get("freshness"),
            "disclaimer": "Probabilités statistiques estimées ; aucune garantie ; aucun conseil de pari.", "selections": out}


@app.get("/v1/teams/{slug}", tags=["données"], summary="Profil d'une équipe (forme, xG approché, Elo)")
def equipe(slug: str, _=Depends(cle_valide)):
    t = next((x for x in lire("teams.json", []) if x["slug"] == slug), None)
    if not t:
        raise HTTPException(404, "équipe inconnue")
    return t


@app.get("/v1/standings/{competition}", tags=["données"])
def classement(competition: str, _=Depends(cle_valide)):
    rows = (lire("standings.json", {}) or {}).get(competition)
    if rows is None:
        raise HTTPException(404, "classement indisponible")
    return {"competition": competition, "standings": rows}


@app.get("/v1/performance", tags=["données"], summary="Performance hors échantillon et calibration du modèle")
def performance(_=Depends(cle_valide)):
    return lire("performance.json", {})


@app.exception_handler(Exception)
async def erreur(_: Request, exc: Exception):                       # jamais de trace interne renvoyée au client
    print("erreur API :", repr(exc), flush=True)
    return JSONResponse(status_code=500, content={"detail": "erreur interne"})
