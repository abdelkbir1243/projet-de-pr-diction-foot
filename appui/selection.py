"""Page « Sélection du jour » : pour chaque match, la sélection statistique la plus robuste, une analyse prudente ou une abstention.

Les décisions viennent du pipeline (footpred/selection_prod.py) avec des seuils appris sur la validation chronologique
(footpred/artefacts/selection.json). Cette page n'invente rien : elle affiche, filtre et explique.
"""
import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st

from .donnees import PARIS, date_longue, heure, jour, maintenant, tout
from .ui import carte, e, ecusson, html_, pct, styles, tuile

ART = os.path.join(os.path.dirname(__file__), "..", "footpred", "artefacts", "selection.json")
DECISION = {"retenue": ("Sélection retenue", "A", "Élevée"), "prudente": ("Analyse prudente", "B", "Modérée"),
            "abstention": ("Abstention", "C", "Faible")}
MODES = ["Meilleur compromis", "Plus probable", "Plus prédictible"]


@st.cache_data(ttl=3600, show_spinner=False)
def artefact() -> dict:
    try:
        return json.load(open(ART, encoding="utf-8"))
    except OSError:
        return {}


def _pill(dec: str) -> str:
    lab, cls, _ = DECISION.get(dec, ("—", "ft", "—"))
    return f'<span class="gg-pill gg-{cls}">{e(lab)}</span>'


def _choix(sel: dict, mode: str):
    return sel.get("plusProbable") if mode == "Plus probable" else sel.get("choix")


def page():
    styles()
    from .pages import bandeau
    bandeau()
    d, art = tout(), artefact()
    sels = d.get("selections") or {}
    st.markdown("### Sélection du jour")
    st.caption("Pour chaque match : la sélection statistique la plus robuste, une analyse prudente, ou une abstention. "
               "Probabilités estimées, jamais des certitudes ; aucun conseil de pari.")
    if not sels:
        st.info("Aucune sélection publiée pour le moment : elles sont calculées pour les matchs à venir des 5 grands championnats "
                "dont l'horaire est connu, avant le coup d'envoi.")
        return
    jours = sorted(sels)
    auj = maintenant().astimezone(PARIS).date().isoformat()
    defaut = auj if auj in jours else next((j for j in jours if j >= auj), jours[-1])
    c1, c2 = st.columns([2, 3])
    j = c1.selectbox("Date analysée", jours, index=jours.index(defaut), format_func=lambda x: ("Aujourd'hui · " if x == auj else "") + date_longue(x).capitalize())
    mode = c2.segmented_control("Affichage", MODES, default=MODES[0]) or MODES[0]
    S = sels[j]
    matchs = {m["slug"]: m for m in d["matches"]}
    items = [it for it in S["items"]]

    with st.expander("Filtres", expanded=False):
        f1, f2, f3 = st.columns(3)
        comps = sorted({it["competition"] for it in items})
        noms_c = {c["slug"]: c["name"] for c in d["competitions"]}
        fc = f1.multiselect("Championnat", comps, format_func=lambda s: noms_c.get(s, s))
        fd = f2.multiselect("Décision", list(DECISION), format_func=lambda s: DECISION[s][0])
        fam = sorted({(it.get("choix") or {}).get("famille") for it in items if it.get("choix")})
        ff = f3.multiselect("Type de marché", fam)
        g1, g2, g3 = st.columns(3)
        eq = g1.text_input("Équipe", placeholder="ex. Arsenal")
        g2.radio("Type", ["Avant-match", "Live"], horizontal=True, index=0, disabled=True,
                 help="Le modèle live (probabilités pendant le match) nécessite un flux d'événements en direct, pas encore branché.")
        avec_cotes = g3.toggle("Seulement avec comparaison aux cotes", value=False)
    def garde(it):
        c = _choix(it, mode) or {}
        return ((not fc or it["competition"] in fc) and (not fd or it["decision"] in fd) and (not ff or c.get("famille") in ff)
                and (not eq or eq.lower() in (it["homeName"] + " " + it["awayName"]).lower())
                and (not avec_cotes or c.get("ref_source", "").startswith("marché")))
    vus = [it for it in items if garde(it)]
    if mode == "Plus prédictible":
        vus.sort(key=lambda it: (it.get("qualite", 0) < 60, it.get("entropie", 1)))

    # ---------------- en-tête
    maj = datetime.fromisoformat(S["generatedAt"]).astimezone(PARIS)
    html_('<div class="gg-tiles" style="padding:0">' + tuile("Date analysée", e(date_longue(j).split(" ", 1)[1])) + tuile("Matchs", S["matches"])
          + tuile("Sélections retenues", S["retained"]) + tuile("Analyses prudentes", S["prudent"]) + tuile("Abstentions", S["abstentions"])
          + tuile("Couverture", pct(S["coverage"]), "matchs avec sélection retenue") + tuile("Mise à jour", f"{maj:%H:%M}", f"{maj:%d/%m}") + "</div>")

    # ---------------- synthèse
    t = art.get("test_T") or {}
    ret = [it for it in items if it["decision"] == "retenue"]
    meilleures = sorted(ret, key=lambda it: -(it["choix"]["p"] - it["choix"]["ref"]))[:3]
    eviter = [it for it in items if it["decision"] == "abstention"][:3]
    pred = [matchs[s] for s in S.get("mostPredictable", []) if s in matchs]
    li = lambda xs: "".join(f"<li>{x}</li>" for x in xs) or "<li>—</li>"
    nom_m = lambda x: e(x["homeName"]) + " – " + e(x["awayName"])
    l1 = [nom_m(it) + " : " + e(it["choix"]["marche"]) + " (" + pct(it["choix"]["p"]) + ")" for it in meilleures]
    l2 = [nom_m(m) for m in pred]
    l3 = [nom_m(it) for it in eviter]
    l4 = [e(r) + f" ({n})" for r, n in S.get("reasons", [])]
    corps = ('<div class="gg-list" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:4px 18px">'
             f"<div><b>Meilleures sélections statistiques</b><ul>{li(l1)}</ul></div>"
             f"<div><b>Matchs les plus prédictibles</b><ul>{li(l2)}</ul></div>"
             f"<div><b>Matchs à éviter</b><ul>{li(l3)}</ul></div>"
             f"<div><b>Principales raisons d'incertitude</b><ul>{li(l4)}</ul></div></div>")
    note = (f"Confiance moyenne (borne basse) des sélections retenues : {pct(S['meanConfidenceRetained'])}. " if S.get("meanConfidenceRetained") else "")
    if t.get("retenue"):
        note += (f"Test final réservé {t.get('saison')} ({t.get('matchs')} matchs) : {pct(t['retenue']['couverture'])} des matchs retenus, "
                 f"réussite observée {pct(t['retenue']['reussite'], 1)} pour {pct(t['retenue']['annonce'], 1)} annoncés ; "
                 f"prudentes {pct(t['prudente']['reussite'], 1)} pour {pct(t['prudente']['annonce'], 1)}.")
    fr = S.get("freshness") or {}
    if fr.get("stale"):
        note += f" Données en retard (dernier résultat {fr.get('lastResult')}) : les sélections sont suspendues tant que les résultats manquent."
    html_(carte("Synthèse Goalgebra du jour", corps, bande=True, note=e(note)))

    # ---------------- tableau
    if not vus:
        st.info("Aucun match pour ces filtres."); return
    lignes = []
    for it in vus:
        c = _choix(it, mode)
        lignes.append({"Heure": heure(matchs[it["match"]]) if it["match"] in matchs else it["kickoff"][11:16], "Match": f'{it["homeName"]} – {it["awayName"]}',
                       "Meilleure prédiction": c["marche"] if c else "Aucune", "Probabilité": c["p"] if c else float("nan"), "Borne basse": c["p_bas"] if c else float("nan"),
                       "Référence": c["ref"] if c else float("nan"), "Confiance": DECISION[it["decision"]][2], "Qualité": it.get("qualite"),
                       "Décision": DECISION[it["decision"]][0]})
    st.dataframe(pd.DataFrame(lignes), hide_index=True, width="stretch",
                 column_config={"Probabilité": st.column_config.NumberColumn(format="percent"), "Borne basse": st.column_config.NumberColumn(format="percent"),
                                "Référence": st.column_config.NumberColumn(format="percent", help="Probabilité du marché sans marge si une cote existe, sinon fréquence historique"),
                                "Qualité": st.column_config.ProgressColumn(format="%d/100", min_value=0, max_value=100)})
    st.caption("Mode « Meilleur compromis » : parmi les sélections dont même la borne basse dépasse la référence, celle qui apporte le plus de "
               "succès attendus en plus de la référence. « Plus probable » : probabilité calibrée maximale (souvent triviale). "
               "« Plus prédictible » : matchs classés par incertitude (entropie) croissante.")

    # ---------------- détail
    st.markdown("#### Détail par match")
    for it in vus:
        m = matchs.get(it["match"], {})
        full = m.get("selection") or it
        c = _choix(it, mode)
        titre = f'{it["homeName"]} – {it["awayName"]} · {DECISION[it["decision"]][0]}' + (f' · {c["marche"]} {pct(c["p"])}' if c else "")
        with st.expander(titre):
            detail(it, full, c, art)


def detail(it: dict, full: dict, c: dict | None, art: dict):
    html_(f'<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">{ecusson(it["home"], 28)}<b>{e(it["homeName"])}</b> – '
          f'<b>{e(it["awayName"])}</b>{ecusson(it["away"], 28)} {_pill(it["decision"])}'
          f'<a href="match?m={e(it["match"])}" target="_self" style="margin-left:auto">fiche du match →</a></div>')
    if c:
        txt = (f'**Meilleure sélection statistique : {c["marche"]}** — probabilité estimée {pct(c["p"])}, borne basse {pct(c["p_bas"])} '
               f'(référence {pct(c["ref"])}, {c.get("ref_source", "")}). Écart avec la référence : {100 * (c["p"] - c["ref"]):+.1f} points.')
        if c.get("cote"):
            txt += f' Cote observée {c["cote"]:.2f} · espérance {c["ev"]:+.1%} · espérance prudente (borne basse) {c["ev_prudente"]:+.1%}.'
            if c.get("ev_prudente", -1) <= 0:
                txt += " **Probabilité élevée, mais aucune valeur statistique détectée.**"
        st.markdown(txt)
    if it.get("raisons"):
        st.markdown("Raisons : " + " ; ".join(it["raisons"]) + ".")
    fam = (art.get("fiabilite_familles_B") or {}).get((c or {}).get("famille"))
    if fam:
        st.caption(f'Fiabilité historique des sélections retenues de la famille « {c["famille"]} » (validation 2021-2024) : '
                   f'{pct(fam["reussite"], 1)} réussies pour {pct(fam["annonce"], 1)} annoncées, {fam["n"]} sélections.')
    if full.get("fige"):
        st.info(f'Sélection figée le {full.get("createdAt", "?")[:16].replace("T", " ")} UTC, avant le coup d\'envoi (version {full.get("modelVersion")}).'
                + ("" if full.get("resultat") is None else (" Résultat : ✅ réussie." if full["resultat"] == 1 else " Résultat : ❌ ratée.")))
    if "candidats" not in full:
        return
    t1, t2, t3, t4 = st.tabs(["Tous les marchés", "Modèles et incertitude", "Facteurs", "Qualité des données"])
    with t1:
        st.dataframe(pd.DataFrame([{"Marché": k["marche"], "Famille": k["famille"], "Probabilité": k["p"], "Borne basse": k["p_bas"], "Référence": k["ref"],
                                    "Source": k["ref_source"], "Écart (pts)": round(100 * k["ecart"], 1), "Information (bits)": round(k["info"], 3),
                                    "Cote": k.get("cote"), "Espérance": k.get("ev")} for k in full["candidats"]]),
                     hide_index=True, width="stretch", column_config={k: st.column_config.NumberColumn(format="percent") for k in ("Probabilité", "Borne basse", "Référence", "Espérance")})
        st.caption("Tous les marchés sont dérivés d'une même distribution des scores (Dixon-Coles repondérée sur les probabilités 1X2) : "
                   "ils sont mathématiquement cohérents entre eux. Les combinaisons de sélections ne sont pas proposées.")
        sc = pd.DataFrame(full.get("scores", []))
        if len(sc):
            st.bar_chart(sc.set_index("score")["p"], height=180)
    with t2:
        mods = full.get("modeles", {})
        rows = [{"Modèle": k, "1": v[0], "N": v[1], "2": v[2]} for k, v in mods.items()]
        rows.append({"Modèle": f'Probabilités retenues ({full.get("source_1x2")})', "1": full["p_1x2"][0], "N": full["p_1x2"][1], "2": full["p_1x2"][2]})
        if full.get("marche_1x2"):
            rows.append({"Modèle": f'Marché sans marge (marge {pct(full.get("marge"), 1)})', "1": full["marche_1x2"][0], "N": full["marche_1x2"][1], "2": full["marche_1x2"][2]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={k: st.column_config.NumberColumn(format="percent") for k in "1N2"})
        html_('<div class="gg-tiles" style="padding:0">' + tuile("Désaccord entre modèles", f'{full["desaccord"]:.2f}', "distance maximale (0 = identiques)")
              + tuile("Entropie 1-N-2", f'{full["entropie"]:.2f}', "0 = certain · 1 = uniforme") + tuile("Confiance (borne basse)", pct(full.get("confiance"))) + "</div>")
    with t3:
        ex = full.get("explication") or {}
        cols = st.columns(3)
        for col, (k, lab) in zip(cols, (("domicile", "Favorables au domicile"), ("nul", "Augmentent le nul"), ("exterieur", "Favorables à l'extérieur"))):
            col.markdown(f"**{lab}**")
            for f in ex.get(k, []) or [{"variable": "—", "effet": 0}]:
                col.markdown(f'- {f["variable"]}' + (f' ({f["effet"]:+.2f})' if f["effet"] else ""))
        st.caption(ex.get("note", ""))
    with t4:
        ctl = full.get("controles", {})
        st.markdown("\n".join(f'- {"✅" if v else "⚠️"} {k}' for k, v in ctl.items()))
        st.caption(f'Score de qualité : {full.get("qualite")}/100 (part des contrôles satisfaits). Les contrôles « horaire fiable », '
                   "« données à jour » et « variables complètes » sont bloquants.")
