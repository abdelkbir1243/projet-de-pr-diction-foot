"""Assistant statistique de l'application Streamlit (même moteur que web/lib/assistant.ts).

Moteur local, gratuit : comprend des questions simples en français et répond uniquement à partir des données publiées
(matchs, équipes, classements, performances). Il ne recommande jamais de pari.
Avec le secret ANTHROPIC_API_KEY, Claude reformule et approfondit la réponse à partir des mêmes données.
"""
import json
import os
import re
import unicodedata
import urllib.request
from datetime import datetime, timedelta, timezone

from .donnees import maintenant, tout

MODELE_LLM = "claude-sonnet-4-5"
SYSTEME = """Tu es l'assistant statistique de Goalgebra, une plateforme académique d'analyse du football.
Règles :
- Réponds en français, en 2 à 8 phrases ou une courte liste, sans titre.
- Utilise UNIQUEMENT les données fournies dans <donnees>. Si une information manque, dis-le simplement. N'invente aucun chiffre, joueur, blessure ou actualité.
- Présente des probabilités et des statistiques, jamais des certitudes : n'écris jamais « garanti », « sûr », « 100 % ».
- Ne donne aucun conseil de pari ni de mise. Si on te demande quoi parier, explique le niveau de risque statistique et rappelle que le modèle ne bat pas les cotes en moyenne."""

STOP = {"fc", "ac", "as", "sc", "afc", "cf", "de", "la", "le", "real", "united", "city", "club", "sv", "tsg", "1", "madrid", "manchester",
        "borussia", "athletic", "atletico", "hotspur", "albion", "town", "hove", "saint", "germain", "deportivo", "racing", "sporting",
        "olympique", "stade"}
ALIAS = {"psg": "paris-saint-germain", "barca": "barcelona", "om": "marseille", "ol": "lyon", "bayern": "bayern-munich",
         "atletico": "atletico-madrid", "juve": "juventus", "spurs": "tottenham-hotspur", "gladbach": "borussia-monchengladbach",
         "real": "real-madrid", "inter": "inter", "milan": "ac-milan"}
COMP_ALIAS = {"premier-league": ["premier league", "angleterre", "anglais", "pl"], "laliga": ["laliga", "la liga", "liga", "espagne", "espagnol"],
              "serie-a": ["serie a", "italie", "calcio"], "bundesliga": ["bundesliga", "allemagne"], "ligue-1": ["ligue 1", "france", "l1"],
              "champions-league": ["ligue des champions", "champions league", "ldc", "ucl"], "europa-league": ["ligue europa", "europa league", "uel"],
              "conference-league": ["conference league", "uecl"]}
GLOSSAIRE = [
    (r"\bxg\b|expected goals|buts attendus", "Les **buts attendus (xG)** estiment combien de buts une équipe « aurait dû » marquer d'après ses occasions. "
     "Ici, c'est une approximation : tirs cadrés × taux de conversion de la ligue (estimé sur les saisons précédentes). "
     "Sur une prédiction, « xG » désigne les buts attendus par le modèle pour ce match."),
    (r"\belo\b", "Le **classement Elo** mesure le niveau global d'une équipe : il monte après une victoire, d'autant plus que l'adversaire est fort. "
     "100 points d'écart ≈ 64 % de chances de gagner hors avantage du terrain."),
    (r"log loss|logloss", "La **log loss** pénalise les prédictions confiantes qui se trompent. Plus elle est basse, mieux c'est ; environ 1,07 correspond à "
     "des prédictions sans information, les cotes des bookmakers font environ 0,97."),
    (r"brier", "Le **score de Brier** est l'écart quadratique moyen entre probabilités annoncées et résultats (0 = parfait)."),
    (r"calibr", "Un modèle **calibré** annonce 40 % pour des issues qui se réalisent 40 % du temps. La page Performance montre la courbe de calibration."),
    (r"confiance|fiabilit|niveau a|niveau b|niveau c", "Le **degré de confiance** (A, B, C) combine l'accord avec les cotes, l'avancement de la saison et la "
     "netteté du favori. Il est vérifié sur des matchs que le modèle n'avait pas vus : on affiche la fréquence réelle observée."),
]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


def P(x, d=0):
    return "—" if x is None else f"{100 * x:.{d}f} %".replace(".", ",")


def ent(x) -> str:
    return f"{int(x):,}".replace(",", "\u202f")


def N(x, d=1):
    return "—" if x is None else f"{x:.{d}f}".replace(".", ",")


def equipes_citees(question: str) -> list[dict]:
    d = tout()
    equipes = list(d["teams"].values())
    t = f" {norm(question)} "
    trouve = []                                       # (équipe, position, longueur)
    couvert = lambda pos: any(f[1] <= pos < f[1] + f[2] + 1 for f in trouve)
    for eq in equipes:                                # 1) noms complets, courts, slugs
        for n in map(norm, (eq["name"], eq.get("short") or "", eq["slug"].replace("-", " "))):
            pos = t.find(f" {n} ")
            if len(n) >= 3 and pos >= 0:
                trouve.append((eq, pos, len(n))); break
    for a, sl in ALIAS.items():                       # 2) surnoms
        pos = t.find(f" {a} ")
        eq = d["teams"].get(sl)
        if pos >= 0 and eq and not couvert(pos) and all(f[0] is not eq for f in trouve):
            trouve.append((eq, pos, len(a)))
    for eq in equipes:                                # 3) un mot distinctif du nom
        if any(f[0] is eq for f in trouve):
            continue
        for w in (w for w in norm(eq["name"]).split() if len(w) >= 4 and w not in STOP):
            pos = t.find(f" {w} ")
            if pos >= 0 and not couvert(pos):
                trouve.append((eq, pos, len(w))); break
    trouve.sort(key=lambda f: (f[1], -f[2]))
    out, positions = [], set()
    for eq, pos, _ in trouve:
        if eq not in out and pos not in positions:
            out.append(eq); positions.add(pos)
    return out


def _ko(m):
    return datetime.fromisoformat(m["kickoff"].replace("Z", "+00:00"))


def prochain_match(slug):
    t = maintenant() - timedelta(hours=3)
    return next((m for m in tout()["matches"] if slug in (m["home"], m["away"]) and m["status"] == "scheduled" and _ko(m) > t), None)


def match_entre(a, b):
    ms = [m for m in tout()["matches"] if {m["home"], m["away"]} == {a, b}]
    return next((m for m in ms if m["status"] == "scheduled"), ms[-1] if ms else None)


def decrire_match(m) -> list[str]:
    p = m.get("prediction")
    out = [f'**{m["homeName"]} – {m["awayName"]}** ({_ko(m).date().strftime("%d/%m/%Y")})']
    if m["status"] == "finished" and m.get("score"):
        out.append(f'Résultat : {m["score"]["home"]}–{m["score"]["away"]}.')
    if not p:
        out.append("Pas de prédiction disponible pour ce match."); return out
    out.append(f'Probabilités du modèle : {m["homeName"]} {P(p["home"])}, nul {P(p["draw"])}, {m["awayName"]} {P(p["away"])}.')
    out.append(f'Buts attendus {N(p["xg"]["home"])} – {N(p["xg"]["away"])} · score le plus probable {p["likelyScore"]["home"]}–{p["likelyScore"]["away"]} '
               f'({P(p["likelyScore"]["p"])}) · plus de 2,5 buts {P(p.get("over25"))} · les deux marquent {P(p.get("btts"))}.')
    ex = p.get("expected") or {}
    if ex.get("corners"):
        out.append(f'Corners attendus {N(ex["corners"]["mean"])} (80 % des cas entre {ex["corners"]["range"][0]} et {ex["corners"]["range"][1]}), '
                   f'cartons jaunes {N((ex.get("cards") or {}).get("mean"))}.')
    if (p.get("context") or {}).get("notes"):
        out.append("Contexte : " + " ; ".join(p["context"]["notes"]) + ".")
    if p.get("similar"):
        s = p["similar"]
        out.append(f'Dans {s["n"]} matchs comparables : victoire à domicile {P(s["homeWin"])}, nul {P(s["draw"])}, victoire à l\'extérieur {P(s["awayWin"])}, '
                   f'{N(s["avgGoals"], 2)} buts en moyenne.')
    if p.get("market"):
        mk = p["market"]
        out.append(f'Marché (cotes, marge retirée) : {P(mk["home"])} / {P(mk["draw"])} / {P(mk["away"])} — {mk["agreement"]} avec le modèle.')
    tr = p.get("trust")
    if tr:
        out.append(f'Degré de confiance **{tr["level"]}** ({tr.get("label", "")}). Ce n\'est jamais une certitude.')
    return out


def decrire_equipe(t) -> list[str]:
    s = t.get("stats") or {}
    rang = f'{t["rank"]}{"er" if t["rank"] == 1 else "e"}, {t.get("points")} pts' if t.get("rank") else "classement indisponible"
    out = [f'**{t["name"]}** — {rang} · Elo {N(t.get("elo"), 0)}']
    forme = " ".join({"W": "V", "D": "N", "L": "D"}.get(r, r) for r in t.get("form", [])) or "—"
    out.append(f'Forme (5 derniers) : {forme} · {N(s.get("ppg"), 2)} pts/match sur {s.get("window", "—")} matchs.')
    out.append(f'Buts marqués {N(s.get("goalsFor"), 2)} / encaissés {N(s.get("goalsAgainst"), 2)} par match · xG {N(s.get("xgFor"), 2)} pour, {N(s.get("xgAgainst"), 2)} contre.')
    out.append(f'Corners {N(s.get("corners"))} par match · cartons jaunes {N(s.get("yellow"), 2)} · clean sheets {P(s.get("cleanSheetPct"))} · '
               f'matchs à +2,5 buts {P(s.get("over25Pct"))}.')
    return out


def comparer(a, b) -> list[str]:
    sa, sb = a.get("stats") or {}, b.get("stats") or {}
    lignes = [("Points / match", sa.get("ppg"), sb.get("ppg"), 2), ("Buts marqués / match", sa.get("goalsFor"), sb.get("goalsFor"), 2),
              ("Buts encaissés / match", sa.get("goalsAgainst"), sb.get("goalsAgainst"), 2), ("xG pour / match", sa.get("xgFor"), sb.get("xgFor"), 2),
              ("xG contre / match", sa.get("xgAgainst"), sb.get("xgAgainst"), 2), ("Corners / match", sa.get("corners"), sb.get("corners"), 1),
              ("Elo", a.get("elo"), b.get("elo"), 0)]
    return [f'**{a["name"]} vs {b["name"]}** (10 derniers matchs)'] + [f"- {k} : {N(x, d)} contre {N(y, d)}" for k, x, y, d in lignes]


def repondre(question: str) -> dict:
    """→ {"texte", "liens": [(libellé, url)], "contexte"}"""
    d = tout()
    q = norm(question)
    a = lambda mots: any(w in q for w in mots)
    eqs = equipes_citees(question)
    liens = []

    if a(["cote", "pari", "parier", "recommand", "conseil", "risque", "sure", "prudent", "value", "safe"]) and not eqs:
        mk = d["markets"]
        bas = [r for r in mk.get("rows", []) if r["family"] != "Double chance" and r["p"] < 0.95][:5]
        lignes = ["Je classe les issues par **niveau de risque statistique** ; je ne donne pas de conseil de pari.",
                  "Issues les plus probables selon le modèle parmi les prochains matchs :"]
        lignes += [f'- {r["homeName"]} – {r["awayName"]} : {r["market"]} — {P(r["p"])} (palier {r["tier"][4:]}, cote juste {N(r["fairOdds"], 2)})' for r in bas]
        t = (mk.get("tiers") or [None])[0]
        if t:
            lignes.append(f'Sur {ent(t["decisions"])} issues du palier le moins risqué testées, {P(t["observed"], 1)} se sont réalisées pour {P(t["predicted"], 1)} annoncé, '
                          f'mais le rendement aux cotes réelles est de {N(100 * t["returnAtOdds"])} % : moins de risque ne veut pas dire meilleure affaire.')
        liens.append(("Cotes & risque", "cotes"))
        return {"texte": "\n".join(lignes), "liens": liens, "contexte": "\n".join(lignes)}

    if len(eqs) >= 2:
        x, y = eqs[:2]
        m = match_entre(x["slug"], y["slug"])
        lignes = decrire_match(m) if m else comparer(x, y) + ["Aucun match entre ces deux équipes n'est programmé dans les données publiées."]
        if m:
            liens.append((f'{m["homeName"]} – {m["awayName"]}', f'match?m={m["slug"]}'))
        liens += [(x["name"], f'equipes?t={x["slug"]}'), (y["name"], f'equipes?t={y["slug"]}')]
        return {"texte": "\n".join(lignes), "liens": liens, "contexte": "\n".join(lignes + decrire_equipe(x) + decrire_equipe(y))}

    if len(eqs) == 1:
        t = eqs[0]
        lignes = decrire_equipe(t)
        m = prochain_match(t["slug"])
        if m:
            lignes += ["", "Prochain match :"] + decrire_match(m)
            liens.append((f'{m["homeName"]} – {m["awayName"]}', f'match?m={m["slug"]}'))
        liens.append((t["name"], f'equipes?t={t["slug"]}'))
        return {"texte": "\n".join(lignes), "liens": liens, "contexte": "\n".join(lignes)}

    a_mot = lambda w: f" {w} " in f" {q} "
    comp = next((c for c in d["competitions"] if a_mot(norm(c["name"])) or any(a_mot(x) for x in COMP_ALIAS.get(c["slug"], []))), None)
    if comp:
        rows = d["standings"].get(comp["slug"], [])[:5]
        nom = lambda s: (d["teams"].get(s) or d["index"].get(s) or {}).get("name", s)
        lignes = [f'**{comp["name"]}** — saison {comp.get("season") or ""}']
        lignes += [f'{r["rank"]}. {nom(r["team"])} — {r["points"]} pts ({r["played"]} matchs, {"+" if r["gd"] > 0 else ""}{r["gd"]})' for r in rows]
        s = comp.get("stats")
        if s:
            lignes.append(f'{N(s["goalsPerMatch"], 2)} buts par match · victoire à domicile {P(s["homeWinPct"])} · +2,5 buts {P(s["over25Pct"])}.')
        liens.append((comp["name"], "competitions"))
        return {"texte": "\n".join(lignes), "liens": liens, "contexte": "\n".join(lignes)}

    if a(["performance", "precision", "precis", "modele", "taux de reussite", "accuracy", "fiable"]):
        p = d["performance"]
        if p:
            lignes = [f'Le modèle a été évalué sur **{ent(p["matches"])} matchs** qu\'il n\'avait jamais vus.',
                      f'Bonne issue prédite {P(p["accuracy"], 1)} (cotes {P(p["market"]["accuracy"], 1)}) · log loss {N(p["logLoss"], 3)} '
                      f'(cotes {N(p["market"]["logLoss"], 3)}) · Brier {N(p["brier"], 3)} · calibration (ECE) {N(p["ece"], 3)}.',
                      "Il est bien calibré mais reste un peu moins précis que les cotes des bookmakers, qui intègrent compositions et blessures."]
            liens.append(("Performance de l'IA", "performance"))
            return {"texte": "\n".join(lignes), "liens": liens, "contexte": "\n".join(lignes)}

    for motif, txt in GLOSSAIRE:
        if re.search(motif, q):
            return {"texte": txt, "liens": [("Méthode", "methode")], "contexte": txt}

    if a(["aujourd", "ce soir", "demain", "week end", "weekend", "prochain", "programme", "calendrier", "matchs"]):
        t0 = maintenant()
        debut = t0.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1 if "demain" in q else 0)
        fin = debut + timedelta(days=4 if a(["week end", "weekend", "prochain", "programme", "calendrier"]) else 1)
        ms = [m for m in d["matches"] if debut <= _ko(m) < fin][:12]
        intro = f"{len(ms)} match(s) :"
        if not ms:                                    # rien sur la période : prochaine journée publiée
            suite = [m for m in d["matches"] if _ko(m) >= debut and m["status"] == "scheduled"]
            if suite:
                j0 = _ko(suite[0]).date()
                ms = [m for m in suite if _ko(m).date() == j0][:12]
                intro = f"Aucun match sur cette période. Prochaine journée, le {j0.strftime('%d/%m/%Y')} ({len(ms)} match(s)) :"
        lignes = [intro] + [
            f'- {m["homeName"]} – {m["awayName"]}' + (f' : {P(m["prediction"]["home"])} / {P(m["prediction"]["draw"])} / {P(m["prediction"]["away"])}' if m.get("prediction") else "")
            + (f' ({m["score"]["home"]}–{m["score"]["away"]})' if m.get("score") and m["status"] == "finished" else "") for m in ms] if ms else ["Aucun match publié sur cette période."]
        liens.append(("Matchs", "matchs"))
        return {"texte": "\n".join(lignes), "liens": liens, "contexte": "\n".join(lignes)}

    texte = "\n".join(["Je réponds à partir des données statistiques de l'application. Exemples :", "- « Analyse Arsenal – Chelsea »",
                       "- « Forme de Barcelona »", "- « Classement de la Serie A »", "- « Quels sont les matchs les moins risqués ? »",
                       "- « Le modèle est-il fiable ? »", "- « C'est quoi les xG ? »", "- « Matchs de demain »"])
    return {"texte": texte, "liens": [], "contexte": ""}


def contexte_global() -> str:
    d = tout(); m = d["meta"]; p = d["performance"] or {}
    return (f'Données calculées le {m.get("generatedAt", "?")[:16]}, résultats jusqu\'au {m.get("dataAsOf")}, mode {m.get("mode")}, modèle {m.get("model")}. '
            f'Performance hors échantillon : {p.get("matches")} matchs, bonne issue {P(p.get("accuracy"), 1)}, log loss {N(p.get("logLoss"), 3)}.')


def reformuler(question: str, local: dict, historique: list[dict], cle: str) -> str | None:
    """Réponse de Claude à partir des mêmes données ; None en cas d'échec (le moteur local répond alors seul)."""
    msgs = []
    for h in historique[-6:]:
        if h["role"] in ("user", "assistant") and (msgs or h["role"] == "user"):
            if msgs and msgs[-1]["role"] == h["role"]:
                msgs[-1] = {"role": h["role"], "content": h["content"][:600]}
            else:
                msgs.append({"role": h["role"], "content": h["content"][:600]})
    if msgs and msgs[-1]["role"] == "user":
        msgs.pop()
    msgs.append({"role": "user", "content": f"<donnees>\n{contexte_global()}\n{local['contexte'] or local['texte']}\n</donnees>\n\nQuestion : {question[:600]}"})
    corps = json.dumps({"model": os.environ.get("ANTHROPIC_MODEL", MODELE_LLM), "max_tokens": 600, "system": SYSTEME, "messages": msgs}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=corps, method="POST",
                                 headers={"content-type": "application/json", "x-api-key": cle, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            j = json.loads(r.read())
        return "\n".join(c["text"] for c in j.get("content", []) if c.get("type") == "text").strip() or None
    except Exception:
        return None
