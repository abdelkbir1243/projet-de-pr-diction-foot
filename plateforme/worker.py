"""Service de calcul (conteneur « worker ») : met à jour les données toutes les INTERVALLE_MIN minutes.

Chaque cycle :
  1. lance le pipeline (python -m footpred.web) dans un dossier temporaire, en reprenant le journal existant ;
  2. remplace atomiquement le dossier de données partagé avec l'application et l'API (GOALGEBRA_DATA_DIR) ;
  3. copie le journal des prédictions en base (table predictions) ;
  4. enregistre l'exécution (succès, échec, durée, fraîcheur) pour la page d'administration ;
  5. en cas d'échec ou de données en retard, envoie une alerte (ALERTE_WEBHOOK : Discord, Slack, ntfy…).

    python -m plateforme.worker            # boucle infinie (conteneur)
    python -m plateforme.worker --une-fois # un seul cycle (test, cron)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

from .db import ExecutionPipeline, Prediction, auditer, maintenant, session

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def dossier_donnees() -> str:
    return os.environ.get("GOALGEBRA_DATA_DIR") or os.path.join(RACINE, "web", "data")


def alerter(texte: str):
    url = os.environ.get("ALERTE_WEBHOOK")
    print("ALERTE :", texte, flush=True)
    if not url:
        return
    corps = json.dumps({"content": texte, "text": texte}).encode()        # Discord (content) et Slack (text)
    try:
        req = urllib.request.Request(url, data=corps, headers={"Content-Type": "application/json", "User-Agent": "goalgebra"})
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as e:
        print("alerte non envoyée :", e, flush=True)


def _instant(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def importer_journal(dossier: str) -> int:
    """journal.json → table predictions. Une prédiction existante n'est jamais modifiée, seul son résultat est complété."""
    f = os.path.join(dossier, "journal.json")
    if not os.path.exists(f):
        return 0
    journal = json.load(open(f, encoding="utf-8"))
    n = 0
    with session() as s:
        for mid, v in journal.items():
            if _instant(v["madeAt"]) >= _instant(v["kickoff"]):
                continue                                                  # jamais de prédiction postérieure au coup d'envoi
            p = s.get(Prediction, mid)
            if p is None:
                s.add(Prediction(id=mid, faite_le=_instant(v["madeAt"]), coup_envoi=_instant(v["kickoff"]), domicile=v.get("home", ""),
                                 exterieur=v.get("away", ""), p_dom=v["pH"], p_nul=v["pD"], p_ext=v["pA"], modele=v.get("model", ""),
                                 resultat=v.get("result"), score=v.get("score")))
                n += 1
            elif v.get("result") and not p.resultat:
                p.resultat, p.score = v["result"], v.get("score")
        s.commit()
    return n


def cycle() -> bool:
    cible = dossier_donnees()
    tmp = cible.rstrip("/") + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    if os.path.exists(os.path.join(cible, "journal.json")):              # le journal se poursuit d'un cycle à l'autre
        shutil.copy(os.path.join(cible, "journal.json"), os.path.join(tmp, "journal.json"))
    with session() as s:
        run = ExecutionPipeline(); s.add(run); s.commit(); rid = run.id
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, "-m", "footpred.web", "--sortie", tmp], cwd=RACINE, capture_output=True, text=True,
                           timeout=int(os.environ.get("PIPELINE_TIMEOUT_S", "2400")))
        meta = json.load(open(os.path.join(tmp, "meta.json"), encoding="utf-8")) if os.path.exists(os.path.join(tmp, "meta.json")) else None
        if r.returncode != 0 or not meta:
            lignes = [l for l in (r.stderr or r.stdout or "").splitlines() if l.strip()]
            raise RuntimeError(lignes[-1] if lignes else f"code {r.returncode}")
        ancien = cible.rstrip("/") + ".old"
        shutil.rmtree(ancien, ignore_errors=True)
        if os.path.exists(cible):
            os.replace(cible, ancien)
        os.replace(tmp, cible)
        shutil.rmtree(ancien, ignore_errors=True)
        n = importer_journal(cible)
        fr = meta.get("freshness") or {}
        nb = len(json.load(open(os.path.join(cible, "matches.json"), encoding="utf-8")))
        with session() as s:
            run = s.get(ExecutionPipeline, rid)
            run.fin, run.statut, run.mode, run.matchs = maintenant(), "succes", meta.get("mode"), nb
            run.dernier_resultat, run.en_retard = fr.get("lastResult"), bool(fr.get("stale"))
            run.message = f"{nb} matchs · {n} prédictions ajoutées au journal · {time.time() - t0:.0f} s · sources : " + ", ".join(meta.get("sources", []))
            auditer(s, "pipeline_succes", run.message); s.commit()
        if fr.get("stale"):
            alerter(f"⚠️ Goalgebra : données en retard (dernier résultat {fr.get('lastResult')}, {fr.get('missingResults', 0)} match(s) sans score).")
        return True
    except Exception as e:
        with session() as s:
            run = s.get(ExecutionPipeline, rid)
            run.fin, run.statut, run.message = maintenant(), "echec", str(e)[:2000]
            auditer(s, "pipeline_echec", str(e)[:500]); s.commit()
        alerter(f"❌ Goalgebra : échec du calcul des données — {str(e)[:300]}")
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--une-fois", action="store_true")
    a = ap.parse_args()
    from .comptes import initialiser_admin
    initialiser_admin()
    cible, embarque = dossier_donnees(), os.path.join(RACINE, "web", "data")
    if not os.path.exists(os.path.join(cible, "meta.json")) and os.path.exists(os.path.join(embarque, "meta.json")) and cible != embarque:
        shutil.copytree(embarque, cible, dirs_exist_ok=True)               # premier démarrage : données livrées avec le code
    if a.une_fois:
        sys.exit(0 if cycle() else 1)
    intervalle = int(os.environ.get("INTERVALLE_MIN", "120")) * 60
    while True:
        debut = time.time()
        cycle()
        time.sleep(max(60, intervalle - (time.time() - debut)))


if __name__ == "__main__":
    main()
