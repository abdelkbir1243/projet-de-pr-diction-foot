"""Pages de l'application Streamlit : Match Center, page match, prédictions, cotes & risque, compétitions, performance."""
import os
from datetime import date, datetime, timedelta, timezone

import altair as alt
import pandas as pd
import streamlit as st

from .donnees import PARIS, date_longue, en_cours, equipe, etat_maj, heure, jour, lancer_maj, maintenant, perimees, tout
from .ui import _passe, barre, carte, e, ecusson, html_, ligne_match, niveau, pct, styles, tuile

MODES = {"live": "Calendrier et scores en direct (football-data.org)", "fixtures": "Calendrier et résultats réels",
         "offline": "Aucune source de calendrier joignable : derniers résultats réels connus",
         "replay": "Journée rejouée : le modèle n'utilise que les données antérieures à cette date"}


def _quand(iso) -> str:
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(PARIS)
    except ValueError:
        return "?"
    return f"{t.day:02d}/{t.month:02d} à {t:%H:%M}"


@st.fragment(run_every=15)
def _suivi_maj():
    """Bandeau de fraîcheur, bouton de mise à jour, et rechargement automatique quand un calcul se termine."""
    m = tout()["meta"]
    et = etat_maj()
    c1, c2 = st.columns([5, 1], vertical_alignment="center")
    with c1:
        mode = m.get("mode")
        src = ", ".join(dict.fromkeys(s.split(" (")[0] for s in m.get("sources", []) if "rejeu" not in s))
        txt = MODES.get(mode, "")
        quand = f'calculé le {_quand(m.get("generatedAt"))}' if mode != "replay" else f'date rejouée {e(m.get("referenceDate", "?"))}'
        if en_cours():
            dt = int((datetime.now(timezone.utc) - et["debut"]).total_seconds() // 60) if et.get("debut") else 0
            html_(f'<div class="gg-banner" style="border-color:#c7d2fe;background:#eef2ff"><span class="gg-pill gg-ai">⟳ mise à jour</span> '
                  f'Récupération des matchs du jour et calcul des prédictions en cours (3 à 8 min, démarré il y a {dt} min). '
                  f'<span class="gg-sub">Affichage actuel : {quand}.</span></div>')
            st.session_state["_maj_attente"] = True
        else:
            html_(f'<div class="gg-banner"><span class="gg-pill gg-ai">{e(mode or "?")}</span> {e(txt)}'
                  f'{f" ({e(src)})" if src and mode != "replay" else ""} '
                  f'<span class="gg-sub">· {quand} · résultats jusqu’au {e(m.get("dataAsOf", "?"))} · modèle {e(m.get("model", ""))}</span></div>')
            fr = m.get("freshness") or {}
            if fr.get("stale"):
                html_('<div class="gg-banner" style="border-color:#fcd34d;background:#fffbeb"><span class="gg-pill gg-B">données en retard</span> '
                      f'Résultats connus jusqu’au {e(fr.get("lastResult", "?"))}'
                      + (f' · {fr["missingResults"]} match(s) joué(s) sans score publié' if fr.get("missingResults") else "")
                      + ' — certaines prédictions n’intègrent pas encore les derniers résultats.</div>')
            if et.get("erreur"):
                st.caption(f"⚠ Dernière tentative de mise à jour impossible : {et['erreur']}")
    from .compte import est_admin, plateforme_active
    if plateforme_active() and not est_admin():
        return                                    # serveur : seuls les administrateurs relancent un calcul
    with c2:
        if st.button("🔄 Mettre à jour", disabled=en_cours(), width="stretch", help="Relance la récupération des matchs et le calcul du modèle"):
            lancer_maj(force=True)
            st.rerun(scope="fragment")
    if not en_cours() and st.session_state.pop("_maj_attente", False):
        st.rerun(scope="app")                     # nouveau calcul disponible : toute la page se recharge


def bandeau():
    if perimees():
        lancer_maj()
    _suivi_maj()


# ================================================================ Match Center
def accueil():
    styles(); bandeau()
    d = tout()
    jours = sorted({jour(m["kickoff"]) for m in d["matches"]})
    if not jours:
        st.info("Aucun match publié pour le moment. Les données sont mises à jour toutes les 2 heures par GitHub Actions.")
        return
    auj = maintenant().astimezone(PARIS).date().isoformat() if not d["meta"].get("now") else jour(d["meta"]["now"])
    defaut = auj if auj in jours else next((j for j in jours if j > auj), jours[-1])
    if "jour" not in st.session_state or st.session_state.jour not in jours:
        st.session_state.jour = defaut

    st.markdown("### Matchs")
    i = jours.index(st.session_state.jour)
    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        if st.button("◀", disabled=i == 0, key="prec"):
            st.session_state.jour = jours[i - 1]; st.rerun()
        choix = st.selectbox("Jour", jours, index=i, label_visibility="collapsed", width="stretch",
                             format_func=lambda j: ("Aujourd'hui · " if j == auj else "") + date_longue(j).capitalize())
        if st.button("▶", disabled=i == len(jours) - 1, key="suiv"):
            st.session_state.jour = jours[i + 1]; st.rerun()
    if choix != st.session_state.jour:
        st.session_state.jour = choix; st.rerun()
    j = st.session_state.jour
    du_jour = [m for m in d["matches"] if jour(m["kickoff"]) == j]
    from .compte import favoris_courants
    fav = set(favoris_courants())
    filtre = st.segmented_control("Filtre", ["Tous", "À venir", "Terminés", "Prédictions IA"] + (["★ Mes équipes"] if fav else []),
                                  default="Tous", label_visibility="collapsed") or "Tous"
    garde = {"★ Mes équipes": lambda m: m["home"] in fav or m["away"] in fav, "Tous": lambda m: True, "À venir": lambda m: m["status"] == "scheduled" and not m.get("started"), "Terminés": lambda m: m["status"] == "finished",
             "Prédictions IA": lambda m: bool(m.get("prediction"))}[filtre]

    gauche, droite = st.columns([2.3, 1], gap="medium")
    with gauche:
        jr = d["days"].get(j)
        if jr and filtre == "Tous":
            html_(resume_journee(jr, j))
        vus = [m for m in du_jour if garde(m)]
        if not vus:
            st.info("Aucun match pour ce filtre.")
        for c in d["competitions"]:
            ms = [m for m in vus if m["competition"] == c["slug"]]
            if ms:
                html_(carte(f'<span class="gg-cc">{e(c["cc"])}</span> {e(c["name"])}', "".join(ligne_match(m) for m in ms),
                            sous_titre=f'{e(c["country"])}' + (f' · {e(c.get("season") or "")}' if c.get("seasonCurrent", True) else ""), droite=f'<span class="gg-sub">{len(ms)}</span>'))
    with droite:
        a_venir = sorted([m for m in d["matches"] if m.get("prediction") and m["status"] == "scheduled" and not m.get("started")],
                         key=lambda m: -max(m["prediction"]["home"], m["prediction"]["away"]))[:3]
        st.caption("À LA UNE · IA")
        for m in a_venir:
            html_(carte_prediction(m))
        perf = d["performance"]
        if perf:
            html_(carte("Performance IA", '<div class="gg-tiles">' + tuile("Bon résultat", pct(perf.get("accuracy"), 1))
                        + tuile("Calibration", f'{perf.get("ece", 0):.3f}') + "</div>",
                        sous_titre=f'{perf.get("matches", 0):,} matchs hors échantillon'.replace(",", " "),
                        note="Le modèle est bien calibré mais reste un peu moins précis que les cotes des bookmakers."))


def resume_journee(jr: dict, j: str) -> str:
    r = jr.get("result") if jr.get("result") and jr["result"]["n"] == jr["n"] else None
    def t(label, x, reel=None):
        sous = f'80 % : {x["range"][0]} à {x["range"][1]}'
        if reel is not None:
            ok = x["range"][0] <= reel <= x["range"][1]
            sous += f'<br><span class="gg-pill gg-{"A" if ok else "B"}">réalisé {reel}</span>'
        return tuile(label, f'{x["expected"]:.1f}'.replace(".", ","), sous)
    tiles = (t("Buts", jr["goals"], r and r["goals"]) + t("Victoires dom.", jr["homeWins"], r and r["homeWins"]) + t("Nuls", jr["draws"], r and r["draws"])
             + t("Victoires ext.", jr["awayWins"], r and r["awayWins"]) + t("+2,5 buts", jr["over25"], r and r["over25"]) + t("Favoris gagnants", jr["favWins"], r and r["favWins"]))
    best = "".join(f'<li><b>{e(b["market"])}</b> — {e(b["homeName"])} – {e(b["awayName"])} : {pct(b["p"])} '
                   f'<span class="gg-sub">(historiquement réalisé {pct(b["observed"])} sur {b["n"]} cas)</span></li>' for b in jr.get("best", []))
    lv = " ".join(f'{niveau(k)} ×{n}' for k, n in jr["levels"].items() if n)
    corps = f'<div class="gg-tiles">{tiles}</div>' + (f'<div class="gg-list"><div class="gg-title" style="margin:4px 0">Statistiques les mieux étayées</div><ul>{best}</ul></div>' if best else "")
    return carte(f"Analyse de la journée · {e(date_longue(j))}", corps, sous_titre=f'{jr["n"]} matchs analysés', droite=lv, bande=True,
                 note="Intervalles où tombe le résultat de la journée 8 fois sur 10 si le modèle est bien calibré. Une statistique probable n'est pas un conseil de pari.")


def carte_prediction(m: dict) -> str:
    p = m["prediction"]
    corps = (f'<a href="match?m={e(m["slug"])}" target="_self" style="text-decoration:none;color:inherit"><div style="padding:12px 14px">'
             f'<div style="display:flex;justify-content:space-between;font-size:13px;font-weight:600;margin-bottom:8px">'
             f'<span style="display:flex;gap:6px;align-items:center">{ecusson(m["home"])}{e(m["homeName"])}</span>'
             f'<span style="display:flex;gap:6px;align-items:center">{e(m["awayName"])}{ecusson(m["away"])}</span></div>'
             f'{barre(p["home"], p["draw"], p["away"])}'
             f'<div class="gg-sub" style="margin-top:6px">buts attendus (λ) {p["xg"]["total"]:.1f} · score probable {p["likelyScore"]["home"]}–{p["likelyScore"]["away"]} · +2,5 {pct(p["over25"])}</div>'
             f'</div></a>')
    lv = (p.get("trust") or {}).get("level")
    return carte('<span style="color:var(--brand)">✦ Prédiction IA</span>', corps, droite=niveau(lv), bande=True)


# ================================================================ Page match
def page_match():
    styles(); bandeau()
    d = tout()
    slug = st.query_params.get("m")
    if not slug or slug not in d["match"]:
        opts = [m["slug"] for m in d["matches"]]
        if not opts:
            st.info("Aucun match publié."); return
        slug = st.selectbox("Choisir un match", opts, format_func=lambda s: f'{d["match"][s]["homeName"]} – {d["match"][s]["awayName"]} ({jour(d["match"][s]["kickoff"])})')
    m = d["match"][slug]; p = m.get("prediction"); c = d["comp"].get(m["competition"], {"name": m["competition"], "cc": "?"})
    sc = m.get("score") if m["status"] in ("finished", "live", "halftime") else None
    milieu = f'{sc["home"]} – {sc["away"]}' if sc else heure(m)
    t_h, t_a = d["teams"].get(m["home"]), d["teams"].get(m["away"])
    info = lambda t: f'<div class="gg-sub">{t["rank"]}{"er" if t["rank"] == 1 else "e"} · {t["points"]} pts</div>' if t and t.get("rank") else ""
    html_(f'<div class="gg-card"><div class="gg-band"></div><div class="gg-head"><div class="gg-title"><span class="gg-cc">{e(c["cc"])}</span> {e(c["name"])}'
          f'{(" · " + e(m["round"])) if m.get("round") else ""}</div><div class="gg-sub">{e(date_longue(jour(m["kickoff"])))}</div></div>'
          f'<div class="gg-hero"><div>{ecusson(m["home"], 64)}<div class="nm">{lien_equipe(m["home"], m["homeName"])}</div>{info(t_h)}</div>'
          f'<div><div class="mid">{milieu}</div><div class="gg-sub">{"Terminé" if m["status"] == "finished" else ("score à 90 min" if m.get("extraTime") else ("score pas encore publié" if m["status"] == "scheduled" and (m.get("awaitingResult") or _passe(m)) else ("coup d’envoi passé" if m.get("started") else "")))}</div></div>'
          f'<div>{ecusson(m["away"], 64)}<div class="nm">{lien_equipe(m["away"], m["awayName"])}</div>{info(t_a)}</div></div></div>')
    if not p:
        st.info("Pas de prédiction pour ce match : une prédiction n'est publiée (et figée au journal) qu'avant le coup d'envoi, "
                "et seulement pour les compétitions couvertes par le modèle.")
        return
    onglets = st.tabs(["Aperçu", "Analyse IA", "xG & forme", "Cotes", "H2H", "Classement"])
    with onglets[0]:
        src = {"pre-match": "Avant-match", "frozen": "Figée avant le match", "out-of-sample": "Hors échantillon"}.get(p.get("source"), "")
        html_(carte('<span style="color:var(--brand)">✦ Prédiction IA</span>', f'<div style="padding:12px 14px">{barre(p["home"], p["draw"], p["away"], True, (m["homeName"], "Nul", m["awayName"]))}</div>'
                    + '<div class="gg-tiles">' + tuile("Score probable", f'{p["likelyScore"]["home"]}–{p["likelyScore"]["away"]}', pct(p["likelyScore"]["p"], 1))
                    + tuile("Buts attendus (λ du modèle)", f'{p["xg"]["total"]:.2f}', f'{p["xg"]["home"]:.2f} – {p["xg"]["away"]:.2f}') + tuile("Plus de 2,5 buts", pct(p["over25"]))
                    + tuile("Les deux marquent", pct(p["btts"])) + "</div>", sous_titre="Probabilités statistiques, jamais des résultats garantis",
                    droite=f'<span class="gg-pill gg-ai">{e(src)}</span>', bande=True))
        tr = p.get("trust")
        if tr:
            ev = tr.get("evidence")
            corps = (f'<div style="padding:12px 14px;font-size:14px">Favori du modèle : <b>{e(tr["favorite"])}</b> à <b>{pct(tr["p"])}</b>.'
                     + (f' Dans <b>{ev["n"]} matchs</b> du même niveau où le favori était annoncé entre {round(100 * ev["from"])} et {round(100 * ev["to"])} %, '
                        f'il l\'a emporté <b>{pct(ev["observed"])}</b> du temps (IC 95 % : {round(100 * ev["lo"])}–{round(100 * ev["hi"])} %).' if ev else "")
                     + "</div><ul class='gg-list'>" + "".join(f'<li>{"✅" if f["effect"] == "plus" else ("⚠️" if f["effect"] == "minus" else "•")} <b>{e(f["label"])}</b> — {e(f["detail"])}</li>' for f in tr["factors"]) + "</ul>")
            html_(carte("Degré de confiance", corps, sous_titre="Mesuré sur des matchs que le modèle n'avait pas vus", droite=niveau(tr["level"], True)))
        ctx = p.get("context")
        if ctx and ctx.get("notes"):
            html_(carte("Contexte du match", "<ul class='gg-list'>" + "".join(f"<li>{e(n)}</li>" for n in ctx["notes"]) + "</ul>",
                        sous_titre="Classement de la veille, repos, statut, enjeu"))
        ex = p.get("expected")
        if ex:
            tl = tuile("Buts", f'{ex["goals"]["mean"]:.1f}', f'80 % : {ex["goals"]["range"][0]} à {ex["goals"]["range"][1]}')
            for k, n in (("corners", "Corners"), ("cards", "Cartons jaunes")):
                if ex.get(k):
                    tl += tuile(n, f'{ex[k]["mean"]:.1f}', f'80 % : {ex[k]["range"][0]} à {ex[k]["range"][1]}')
            html_(carte("Statistiques attendues", f'<div class="gg-tiles">{tl}</div>', sous_titre="Moyenne et intervalle à 80 %"))
            dist = ex["goals"].get("dist")
            if dist:
                df = pd.DataFrame({"buts": [str(i) if i < 6 else "6+" for i in range(len(dist))], "p": dist})
                st.altair_chart(alt.Chart(df).mark_bar(color="#4f46e5", cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                                .encode(x=alt.X("buts:N", sort=None, title="Nombre total de buts"), y=alt.Y("p:Q", axis=alt.Axis(format="%"), title=None),
                                        tooltip=[alt.Tooltip("p:Q", format=".1%")]).properties(height=180), width="stretch")
    with onglets[1]:
        html_(carte("Synthèse de l'IA", f'<div style="padding:12px 14px;font-size:15px;line-height:1.6">{e(p.get("synthesis") or "")}</div>'))
        sim = p.get("similar")
        if sim:
            html_(carte("Matchs comparables", f'<div style="padding:12px 14px">{barre(sim["homeWin"], sim["draw"], sim["awayWin"], True, ("Victoire dom.", "Nul", "Victoire ext."))}</div>',
                        sous_titre=f'Ce qui s\'est réellement passé dans {sim["n"]} matchs semblables',
                        note=f'Buts/match {sim["avgGoals"]:.2f} · +2,5 buts {pct(sim["over25"])} · les deux marquent {pct(sim["btts"])}'))
        if p.get("topScores"):
            st.markdown("**Scores les plus probables**")
            st.dataframe(pd.DataFrame(p["topScores"]).rename(columns={"score": "Score", "p": "Probabilité"}), hide_index=True,
                         column_config={"Probabilité": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=max(s["p"] for s in p["topScores"]))})
        if p.get("markets"):
            st.markdown("**Tous les marchés, du moins risqué au plus risqué**")
            rows = [{"Marché": k["market"], "Famille": k["family"], "Probabilité": k["p"], "Cote juste": round(1 / k["p"], 2) if k["p"] else None,
                     "Réalisé historiquement": (k.get("cal") or {}).get("observed"), "Risque": k["tier"][4:]} for k in p["markets"]]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                         column_config={"Probabilité": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
                                        "Réalisé historiquement": st.column_config.NumberColumn(format="percent")})
            st.caption("Moins de risque = probabilité plus élevée, pas une meilleure décision : sur 2021-2026, aucun palier n'a été rentable aux cotes réelles.")
    with onglets[2]:
        onglet_xg(m)
    with onglets[3]:
        mk = p.get("market")
        if not mk:
            st.info("Aucune cote d'avant-match disponible pour ce match.")
        else:
            html_(carte("Modèle vs marché", f'<div style="padding:12px 14px"><div class="gg-sub">Modèle</div>{barre(p["home"], p["draw"], p["away"])}'
                        f'<div class="gg-sub" style="margin-top:8px">Marché (marge de {pct(mk["margin"], 1)} retirée)</div>{barre(mk["home"], mk["draw"], mk["away"])}</div>',
                        droite=f'<span class="gg-pill gg-{"A" if mk["agreement"] == "accord" else ("B" if "modéré" in mk["agreement"] else "C")}">{e(mk["agreement"])}</span>', note=e(mk["note"])))
            st.dataframe(pd.DataFrame([{"Issue": r["label"], "Modèle": r["model"], "Marché": r["market"], "Écart (pts)": round(100 * r["gap"], 1),
                                        "Cote juste": r["fairOdds"], "Cote": r["odds"]} for r in mk["rows"]]), hide_index=True, width="stretch",
                         column_config={"Modèle": st.column_config.NumberColumn(format="percent"), "Marché": st.column_config.NumberColumn(format="percent")})
    with onglets[4]:
        h = m.get("h2h") or {}
        s = h.get("summary")
        if not s:
            st.info("Aucune confrontation directe dans nos données.")
        else:
            html_(carte("Confrontations directes", f'<div style="padding:12px 14px">{barre(s["homeWins"] / s["n"], s["draws"] / s["n"], s["awayWins"] / s["n"], True, (m["homeName"], "Nuls", m["awayName"]))}</div>'
                        + '<div class="gg-tiles">' + tuile("Buts / match", f'{s["avgGoals"]:.2f}') + tuile("+2,5 buts", pct(s["over25Pct"])) + tuile("Les deux marquent", pct(s["bttsPct"])) + "</div>",
                        sous_titre=f'{s["n"]} derniers matchs'))
            st.dataframe(pd.DataFrame([{"Date": x["date"], "Domicile": equipe(x["home"])["name"], "Score": f'{x["homeGoals"]}–{x["awayGoals"]}', "Extérieur": equipe(x["away"])["name"]}
                                       for x in h["matches"]]), hide_index=True, width="stretch")
    with onglets[5]:
        tableau_classement(m["competition"], surligner=(m["home"], m["away"]))


def tableau_classement(comp_slug: str, surligner=()):
    rows = tout()["standings"].get(comp_slug, [])
    if not rows:
        st.info("Classement non disponible pour cette compétition.")
        return
    df = pd.DataFrame([{"#": r["rank"], "Équipe": ("▶ " if r["team"] in surligner else "") + equipe(r["team"])["name"], "MJ": r["played"], "V": r["won"], "N": r["drawn"],
                        "D": r["lost"], "BP": r["gf"], "BC": r["ga"], "Diff": r["gd"], "Pts": r["points"],
                        "Forme": " ".join({"W": "V", "D": "N", "L": "D"}[x] for x in r["form"])} for r in rows])
    st.dataframe(df, hide_index=True, width="stretch", height=min(38 * len(df) + 40, 760))


# ================================================================ Prédictions IA
def predictions():
    styles(); bandeau(); st.markdown("### Prédictions IA")
    d = tout()
    comps = [c for c in d["competitions"] if c.get("covered") or c.get("model") == "cup"]
    choix = st.segmented_control("Compétition", ["Toutes"] + [c["name"] for c in comps], default="Toutes", label_visibility="collapsed") or "Toutes"
    tri = st.radio("Tri", ["Par date", "Plus forte confiance", "Plus indécis"], horizontal=True, label_visibility="collapsed")
    ms = [m for m in d["matches"] if m.get("prediction") and m["status"] == "scheduled" and not m.get("started") and (choix == "Toutes" or d["comp"][m["competition"]]["name"] == choix)]
    if tri == "Plus forte confiance":
        ms.sort(key=lambda m: -max(m["prediction"]["home"], m["prediction"]["draw"], m["prediction"]["away"]))
    elif tri == "Plus indécis":
        ms.sort(key=lambda m: max(m["prediction"]["home"], m["prediction"]["draw"], m["prediction"]["away"]))
    if not ms:
        st.info("Aucune prédiction à venir pour ce filtre.")
    cols = st.columns(2)
    for i, m in enumerate(ms):
        with cols[i % 2]:
            html_(carte_prediction(m))
    hist = d["performance"].get("history", [])[:30]
    if hist:
        st.markdown("#### Prédictions passées (hors échantillon)")
        lab = {"H": "1", "D": "X", "A": "2"}
        st.dataframe(pd.DataFrame([{"Date": h["date"], "Match": f'{h["homeName"]} – {h["awayName"]}', "Prédiction": lab[h["predicted"]],
                                    "Probabilité": {"H": h["pH"], "D": h["pD"], "A": h["pA"]}[h["predicted"]], "Score": h["score"],
                                    "Résultat": "✅ Correcte" if h["correct"] else "❌ Incorrecte"} for h in hist]),
                     hide_index=True, width="stretch", column_config={"Probabilité": st.column_config.NumberColumn(format="percent")})


# ================================================================ Cotes & risque
def cotes():
    styles(); bandeau(); st.markdown("### Cotes & risque")
    st.warning("Le « risque » est la probabilité que l'issue ne se réalise pas selon le modèle. Sur 2021-2026, aucun palier n'a été rentable aux cotes réelles, "
               "et les cotes restent en moyenne plus précises que le modèle. Cette page sert à comprendre les probabilités, pas à parier.")
    mk = tout()["markets"]
    if mk.get("tiers"):
        st.dataframe(pd.DataFrame([{"Palier": t["tier"][4:], "Issues testées": t["decisions"], "Annoncé": t["predicted"], "Réalisé": t["observed"],
                                    "Rendement aux cotes": t["returnAtOdds"]} for t in mk["tiers"]]), hide_index=True, width="stretch",
                     column_config={k: st.column_config.NumberColumn(format="percent") for k in ("Annoncé", "Réalisé", "Rendement aux cotes")})
    rows = mk.get("rows", [])
    if not rows:
        st.info("Aucun match à venir."); return
    fam = st.segmented_control("Famille", ["Toutes", "Résultat", "Double chance", "Buts", "Corners", "Cartons"], default="Toutes", label_visibility="collapsed") or "Toutes"
    df = pd.DataFrame([{"Match": f'{r["homeName"]} – {r["awayName"]}', "Date": jour(r["kickoff"]), "Issue": r["market"], "Famille": r["family"], "Probabilité": r["p"],
                        "Risque": r["tier"][4:], "Cote juste": r["fairOdds"], "Cote marché": r["odds"]} for r in rows if fam == "Toutes" or r["family"] == fam])
    st.dataframe(df, hide_index=True, width="stretch", height=620,
                 column_config={"Probabilité": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)})


# ================================================================ Compétitions
def competitions():
    styles(); bandeau(); st.markdown("### Compétitions et classements")
    d = tout()
    noms = [c["name"] for c in d["competitions"]]
    nom = st.segmented_control("Compétition", noms, default=noms[0] if noms else None, label_visibility="collapsed") or (noms[0] if noms else None)
    if not nom:
        return
    c = next(x for x in d["competitions"] if x["name"] == nom)
    s = c.get("stats")
    badge = "Prédictions IA" if c.get("covered") else ("Modèle coupes (Elo)" if c.get("model") == "cup" else "Hors modèle")
    if s:
        tl = (tuile("Buts / match", f'{s["goalsPerMatch"]:.2f}', f'{s["matches"]} matchs') + tuile("Victoires domicile", pct(s["homeWinPct"]), f'nuls {pct(s["drawPct"])}')
              + tuile("+2,5 buts", pct(s["over25Pct"]), f'BTTS {pct(s["bttsPct"])}'))
        if s.get("cornersPerMatch") is not None:
            tl += tuile("Corners / match", f'{s["cornersPerMatch"]:.1f}', f'{s["yellowPerMatch"]:.1f} jaunes')
        lib_s = f'saison {e(c.get("season") or "")}' if c.get("seasonCurrent", True) else f'dernière saison disponible : {e(c.get("season") or "")} (la source n’a pas encore publié la saison en cours)'
        html_(carte(f'<span class="gg-cc">{e(c["cc"])}</span> {e(c["name"])}', f'<div class="gg-tiles">{tl}</div>', sous_titre=f'{e(c["country"])} · {lib_s}',
                    droite=f'<span class="gg-pill gg-ai">{badge}</span>'))
    tableau_classement(c["slug"])


# ================================================================ Performance IA
def performance():
    styles(); bandeau(); st.markdown("### Performance de l’IA")
    p = tout()["performance"]
    if not p:
        st.info("Performance non disponible."); return
    st.caption(p.get("scope", ""))
    html_('<div class="gg-tiles" style="padding:0">' + tuile("Matchs évalués", f'{p["matches"]:,}'.replace(",", " "), "hors échantillon")
          + tuile("Bon résultat", pct(p["accuracy"], 1), f'cotes {pct(p["market"]["accuracy"], 1)}') + tuile("Log loss", f'{p["logLoss"]:.3f}', f'cotes {p["market"]["logLoss"]:.3f}')
          + tuile("Brier", f'{p["brier"]:.3f}', f'cotes {p["market"]["brier"]:.3f}') + tuile("Calibration (ECE)", f'{p["ece"]:.3f}', "0 = parfait") + "</div>")
    by = p.get("byDay") or []
    if by:
        st.markdown("#### Suivi jour par jour")
        rows, cg, cge, cf, cfe = [], 0, 0, 0, 0
        for x in by:
            cg += x["goals"]; cge += x["goalsExpected"]; cf += x["favWins"]; cfe += x["favExpected"]
            rows += [{"date": x["date"], "série": "Buts observés", "v": cg}, {"date": x["date"], "série": "Buts attendus", "v": cge},
                     {"date": x["date"], "série": "Favoris gagnants observés", "v": cf}, {"date": x["date"], "série": "Favoris gagnants attendus", "v": cfe}]
        df = pd.DataFrame(rows)
        c1, c2 = st.columns(2)
        for col, cle in ((c1, "Buts"), (c2, "Favoris")):
            sous = df[df["série"].str.startswith(cle)]
            col.altair_chart(alt.Chart(sous).mark_line(strokeWidth=2.5).encode(x=alt.X("date:T", title=None), y=alt.Y("v:Q", title=None),
                             color=alt.Color("série:N", scale=alt.Scale(range=["#9ca3af", "#4f46e5"]), legend=alt.Legend(orient="top", title=None)),
                             strokeDash=alt.condition("indexof(datum['série'], 'attendus') >= 0", alt.value([5, 4]), alt.value([0]))).properties(height=240), width="stretch")
    cal = p.get("calibration") or []
    if cal:
        st.markdown("#### Calibration : probabilité annoncée vs fréquence observée")
        dc = pd.DataFrame(cal)
        diag = alt.Chart(pd.DataFrame({"x": [0, .85], "y": [0, .85]})).mark_line(strokeDash=[4, 4], color="#9ca3af").encode(x="x:Q", y="y:Q")
        pts = alt.Chart(dc).mark_line(point=True, color="#2a78d6").encode(x=alt.X("predicted:Q", axis=alt.Axis(format="%"), title="Annoncé"),
                                                                       y=alt.Y("observed:Q", axis=alt.Axis(format="%"), title="Observé"))
        st.altair_chart((diag + pts).properties(height=300), width="stretch")
    conf = (p.get("confidence") or {}).get("levels")
    if conf:
        st.markdown("#### Fiabilité par degré de confiance")
        st.dataframe(pd.DataFrame([{"Niveau": f'{k} · {v["label"]}', "Part des matchs": v["share"], "Favori annoncé": v["announced"], "Favori réalisé": v["observed"],
                                    "Log loss": v["logLoss"], "Matchs": v["n"]} for k, v in conf.items()]), hide_index=True, width="stretch",
                     column_config={k: st.column_config.NumberColumn(format="percent") for k in ("Part des matchs", "Favori annoncé", "Favori réalisé")})
    _perf_selection()
    cups = p.get("cups")
    if cups:
        st.markdown("#### Coupes d'Europe · modèle Elo")
        noms = {"CL": "Ligue des champions", "EL": "Ligue Europa", "ECL": "Conference League"}
        st.dataframe(pd.DataFrame([{"Compétition": noms.get(k, k), "Matchs": int(v["n"]), "Bon résultat": v["accuracy"], "Log loss": v["logLoss"]} for k, v in cups["byCup"].items()]),
                     hide_index=True, width="stretch", column_config={"Bon résultat": st.column_config.NumberColumn(format="percent")})
        st.caption(f'Log loss {cups["logLoss"]:.3f} contre {cups["baseline"]:.3f} sans information, sur {cups["matches"]} matchs prédits hors échantillon.')


# ================================================================ xG & forme (onglet de la page match)
RADAR = {"attack": "Attaque (xG pour)", "defense": "Défense (xG contre)", "form": "Forme (5 matchs)", "control": "Contrôle (part des tirs)",
         "finishing": "Finition", "venueHome": "À domicile", "venueAway": "À l'extérieur"}


def lien_equipe(slug, nom) -> str:
    if slug and slug in tout()["teams"]:
        return f'<a href="equipes?t={e(slug)}" target="_self" style="color:inherit;text-decoration:none;border-bottom:1px dotted #94a3b8">{e(nom)}</a>'
    return e(nom)


def _finition(s) -> float | None:
    return s["goalsFor"] / s["xgFor"] if s.get("xgFor") and s.get("goalsFor") is not None else None


def _comparatif(lignes, nom_h, nom_a) -> str:
    """Tableau « domicile | indicateur | extérieur » avec barres opposées ; `mieux` = 1 si plus haut est meilleur, -1 sinon."""
    out = (f'<div style="display:grid;grid-template-columns:1fr 1.3fr 1fr;gap:6px 10px;padding:10px 14px;font-size:13px;align-items:center">'
           f'<div style="font-weight:600;color:var(--home)">{e(nom_h)}</div><div></div><div style="font-weight:600;color:var(--away);text-align:right">{e(nom_a)}</div>')
    for lab, a, b, fmt, mieux in lignes:
        if a is None and b is None:
            continue
        tot = (abs(a or 0) + abs(b or 0)) or 1
        ga, gb = (a or 0) * mieux > (b or 0) * mieux, (b or 0) * mieux > (a or 0) * mieux
        out += (f'<div style="display:flex;align-items:center;gap:6px"><b style="min-width:44px;{"" if ga else "font-weight:500;color:var(--t2)"}">{fmt(a)}</b>'
                f'<div style="flex:1;height:6px;background:var(--s2);border-radius:9px;display:flex;justify-content:flex-end">'
                f'<i style="display:block;width:{100 * abs(a or 0) / tot:.0f}%;background:var(--home);opacity:{1 if ga else .4};border-radius:9px"></i></div></div>'
                f'<div style="text-align:center;color:var(--t2);font-size:12px">{e(lab)}</div>'
                f'<div style="display:flex;align-items:center;gap:6px"><div style="flex:1;height:6px;background:var(--s2);border-radius:9px">'
                f'<i style="display:block;width:{100 * abs(b or 0) / tot:.0f}%;height:6px;background:var(--away);opacity:{1 if gb else .4};border-radius:9px"></i></div>'
                f'<b style="min-width:44px;text-align:right;{"" if gb else "font-weight:500;color:var(--t2)"}">{fmt(b)}</b></div>')
    return out + "</div>"


def _f(d=2):
    return lambda x: "—" if x is None else f"{x:.{d}f}".replace(".", ",")


def _forme(t) -> str:
    c = {"W": ("V", "A"), "D": ("N", "B"), "L": ("D", "C")}
    return " ".join(f'<span class="gg-pill gg-{c[r][1]}" style="min-width:18px;justify-content:center">{c[r][0]}</span>' for r in (t.get("form") or []) if r in c)


def lecture_xg(t) -> list[str]:
    s = t.get("stats") or {}
    out, fin = [], _finition(s)
    if s.get("xgFor") is not None and s.get("xgAgainst") is not None:
        diff = s["xgFor"] - s["xgAgainst"]
        out.append(f'{t["name"]} crée {_f()(s["xgFor"])} xG et en concède {_f()(s["xgAgainst"])} par match (différence {"+" if diff >= 0 else ""}{_f()(diff)}).')
    if fin is not None:
        if fin >= 1.2:
            out.append(f"Finition très au-dessus des occasions ({_f()(fin)} but par xG) : ce rendement tend à revenir vers la moyenne.")
        elif fin <= 0.8:
            out.append(f"Finition en dessous des occasions ({_f()(fin)} but par xG) : les buts devraient suivre si le volume d'occasions se maintient.")
    return out


def onglet_xg(m):
    d = tout()
    th, ta = d["teams"].get(m["home"]), d["teams"].get(m["away"])
    if not th or not ta:
        st.info("Statistiques d'équipe indisponibles pour ce match (club hors des 5 championnats couverts).")
        return
    sh, sa = th.get("stats") or {}, ta.get("stats") or {}
    lignes = [("xG créés / match", sh.get("xgFor"), sa.get("xgFor"), _f(), 1), ("xG concédés / match", sh.get("xgAgainst"), sa.get("xgAgainst"), _f(), -1),
              ("Buts marqués / match", sh.get("goalsFor"), sa.get("goalsFor"), _f(), 1), ("Buts encaissés / match", sh.get("goalsAgainst"), sa.get("goalsAgainst"), _f(), -1),
              ("Finition (buts / xG)", _finition(sh), _finition(sa), _f(), 1), ("Tirs / match", sh.get("shots"), sa.get("shots"), _f(1), 1),
              ("Tirs cadrés / match", sh.get("shotsOnTarget"), sa.get("shotsOnTarget"), _f(1), 1),
              ("Part des tirs", sh.get("shotShare"), sa.get("shotShare"), lambda x: pct(x), 1), ("Points / match", sh.get("ppg"), sa.get("ppg"), _f(), 1),
              ("Clean sheets", sh.get("cleanSheetPct"), sa.get("cleanSheetPct"), lambda x: pct(x), 1), ("Corners / match", sh.get("corners"), sa.get("corners"), _f(1), 1),
              ("Elo", th.get("elo"), ta.get("elo"), _f(0), 1)]
    tete = (f'<div style="display:flex;justify-content:space-between;padding:10px 14px 0;gap:8px;flex-wrap:wrap">'
            f'<span>{_forme(th)}</span><span class="gg-sub">5 derniers matchs</span><span>{_forme(ta)}</span></div>')
    notes = lecture_xg(th) + lecture_xg(ta)
    html_(carte("xG et forme · 10 derniers matchs", tete + _comparatif(lignes, m["homeName"], m["awayName"]),
                sous_titre="xG approché = tirs cadrés × taux de conversion de la ligue (saisons précédentes)",
                note=" ".join(e(n) for n in notes) or None, bande=True))
    # Elo des deux équipes
    rows = [{"date": x["date"], "elo": x["elo"], "équipe": t["name"]} for t in (th, ta) for x in (t.get("eloHistory") or [])]
    if rows:
        st.markdown("**Évolution du niveau Elo**")
        st.altair_chart(alt.Chart(pd.DataFrame(rows)).mark_line(strokeWidth=2.5, interpolate="monotone").encode(
            x=alt.X("date:T", title=None), y=alt.Y("elo:Q", scale=alt.Scale(zero=False), title=None),
            color=alt.Color("équipe:N", scale=alt.Scale(domain=[th["name"], ta["name"]], range=["#2a78d6", "#eb6834"]), legend=alt.Legend(orient="top", title=None)),
            tooltip=["équipe", "date:T", "elo:Q"]).properties(height=230), width="stretch")
    # profils (percentiles dans la ligue)
    rr = [{"axe": RADAR.get(k, k), "équipe": t["name"], "v": v} for t in (th, ta) for k, v in (t.get("radar") or {}).items() if v is not None]
    if rr:
        st.markdown("**Profil comparé** · rang centile dans le championnat (100 = meilleur)")
        st.altair_chart(alt.Chart(pd.DataFrame(rr)).mark_bar(cornerRadiusEnd=3).encode(
            y=alt.Y("axe:N", sort=list(RADAR.values()), title=None), x=alt.X("v:Q", scale=alt.Scale(domain=[0, 100]), title=None),
            yOffset="équipe:N", color=alt.Color("équipe:N", scale=alt.Scale(domain=[th["name"], ta["name"]], range=["#2a78d6", "#eb6834"]),
                                                legend=alt.Legend(orient="top", title=None)),
            tooltip=["équipe", "axe", "v:Q"]).properties(height=330), width="stretch")


# ================================================================ Équipes
def equipes():
    styles(); bandeau(); st.markdown("### Équipes")
    d = tout()
    teams = d["teams"]
    if not teams:
        st.info("Aucune équipe publiée."); return
    comps = [c for c in d["competitions"] if any(t["competition"] == c["slug"] for t in teams.values())]
    choisi = st.query_params.get("t")
    comp_def = teams[choisi]["competition"] if choisi in teams else comps[0]["slug"]
    c1, c2 = st.columns([1, 2])
    noms_c = {c["slug"]: c["name"] for c in comps}
    comp = c1.selectbox("Championnat", list(noms_c), index=list(noms_c).index(comp_def), format_func=noms_c.get)
    liste = sorted([t for t in teams.values() if t["competition"] == comp], key=lambda t: (t.get("rank") or 99, t["name"]))
    slugs = [t["slug"] for t in liste]
    idx = slugs.index(choisi) if choisi in slugs else 0
    sl = c2.selectbox("Équipe", slugs, index=idx, format_func=lambda s: f'{teams[s].get("rank") or "–"}. {teams[s]["name"]}')
    if sl != choisi:
        st.query_params["t"] = sl
    t = teams[sl]; s = t.get("stats") or {}
    from .compte import bouton_suivre
    bouton_suivre(sl)
    elo = t.get("eloHistory") or []
    var = elo[-1]["elo"] - elo[-6]["elo"] if len(elo) >= 6 else None
    html_(f'<div class="gg-card"><div class="gg-band"></div><div style="display:flex;gap:16px;align-items:center;padding:16px 18px;flex-wrap:wrap">'
          f'{ecusson(sl, 64)}<div style="flex:1;min-width:180px"><div style="font-size:22px;font-weight:700">{e(t["name"])}</div>'
          f'<div class="gg-sub">{e(noms_c.get(comp, ""))} · {e(t.get("country") or "")}</div><div style="margin-top:6px">{_forme(t)}</div></div>'
          f'<div class="gg-tiles" style="padding:0;flex:2;min-width:280px">'
          + tuile("Classement", f'{t["rank"]}{"er" if t["rank"] == 1 else "e"}' if t.get("rank") else "—", f'{t.get("points", "—")} pts')
          + tuile("Elo", _f(0)(t.get("elo")), (f'{"+" if var >= 0 else ""}{var:.0f} sur 5 matchs' if var is not None else ""))
          + tuile("Points / match", _f()(s.get("ppg")), f'sur {s.get("window", "—")} matchs') + "</div></div></div>")
    fin = _finition(s)
    tl = (tuile("xG créés", _f()(s.get("xgFor")), f'buts marqués {_f()(s.get("goalsFor"))}') + tuile("xG concédés", _f()(s.get("xgAgainst")), f'buts encaissés {_f()(s.get("goalsAgainst"))}')
          + tuile("Finition", _f()(fin), "buts par xG (1 = normal)") + tuile("Tirs", _f(1)(s.get("shots")), f'concédés {_f(1)(s.get("shotsAgainst"))}')
          + tuile("Part des tirs", pct(s.get("shotShare")), "contrôle du jeu") + tuile("Clean sheets", pct(s.get("cleanSheetPct")))
          + tuile("+2,5 buts", pct(s.get("over25Pct")), f'BTTS {pct(s.get("bttsPct"))}') + tuile("Corners", _f(1)(s.get("corners")), f'concédés {_f(1)(s.get("cornersAgainst"))}')
          + tuile("Cartons jaunes", _f(2)(s.get("yellow")), f'rouges {_f(2)(s.get("red"))}'))
    html_(carte("Statistiques · 10 derniers matchs", f'<div class="gg-tiles">{tl}</div>', sous_titre="xG approché à partir des tirs cadrés",
                note=" ".join(e(x) for x in lecture_xg(t)) or None))
    g, dr = st.columns([3, 2], gap="medium")
    with g:
        if elo:
            st.markdown("**Évolution du niveau Elo**")
            st.altair_chart(alt.Chart(pd.DataFrame(elo)).mark_line(color="#4f46e5", strokeWidth=2.5, interpolate="monotone").encode(
                x=alt.X("date:T", title=None), y=alt.Y("elo:Q", scale=alt.Scale(zero=False), title=None),
                                               tooltip=["date:T", "elo:Q"]).properties(height=230), width="stretch")
        dom = [(n, s.get(k) or {}) for n, k in (("Domicile", "home"), ("Extérieur", "away"), (f'Saison {(s.get("season") or {}).get("label", "")}', "season"))]
        st.dataframe(pd.DataFrame([{"": n, "Matchs": x.get("played"), "Pts / match": x.get("ppg"), "Buts pour": x.get("gf"), "Buts contre": x.get("ga"),
                                    "Victoires": x.get("winPct")} for n, x in dom if x]), hide_index=True, width="stretch",
                     column_config={"Victoires": st.column_config.NumberColumn(format="percent")})
    with dr:
        r = t.get("radar") or {}
        if r:
            st.markdown("**Profil** · centile dans le championnat")
            st.altair_chart(alt.Chart(pd.DataFrame([{"axe": RADAR.get(k, k), "v": v} for k, v in r.items() if v is not None])).mark_bar(
                color="#4f46e5", cornerRadiusEnd=3).encode(y=alt.Y("axe:N", sort=list(RADAR.values()), title=None),
                                                           x=alt.X("v:Q", scale=alt.Scale(domain=[0, 100]), title=None), tooltip=["axe", "v:Q"]).properties(height=250), width="stretch")
    prochains = [m for m in d["matches"] if sl in (m["home"], m["away"]) and m["status"] in ("scheduled", "live", "halftime")][:5]
    if prochains:
        html_(carte("Prochains matchs", "".join(ligne_match(m) for m in prochains)))
    der = t.get("lastMatches") or []
    if der:
        st.markdown("**Derniers matchs**")
        st.dataframe(pd.DataFrame([{"Date": x["date"], "Lieu": "Dom." if x["venue"] == "home" else "Ext.", "Adversaire": x["opponentName"],
                                    "Score": f'{x["gf"]}–{x["ga"]}', "Résultat": {"W": "✅ V", "D": "➖ N", "L": "❌ D"}.get(x["result"], x["result"])}
                                   for x in der[:10]]), hide_index=True, width="stretch")


# ================================================================ Assistant
def assistant():
    from . import assistant as A
    styles(); bandeau(); st.markdown("### Assistant statistique")
    cle = None
    try:
        cle = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        cle = None
    cle = cle or os.environ.get("ANTHROPIC_API_KEY")
    st.caption(("Réponses rédigées par Claude à partir des données de l'application. " if cle else "Moteur local : réponses calculées directement à partir des données. ")
               + "Probabilités statistiques uniquement, aucun conseil de pari.")
    if "chat" not in st.session_state:
        st.session_state.chat = []
    exemples = ["Matchs de demain", "Analyse Arsenal – Chelsea", "Forme de Barcelona", "Classement de la Serie A", "Quels sont les matchs les moins risqués ?", "C'est quoi les xG ?"]
    q_ex = st.pills("Exemples", exemples, label_visibility="collapsed", key=f"ex{len(st.session_state.chat)}")
    for h in st.session_state.chat:
        with st.chat_message(h["role"], avatar="🧑" if h["role"] == "user" else "⚽"):
            st.markdown(h["content"].replace("\n", "  \n"))
            if h.get("liens"):
                html_(" ".join(f'<a class="gg-pill gg-ai" href="{e(u)}" target="_self" style="text-decoration:none;margin-right:4px">↗ {e(l)}</a>' for l, u in h["liens"]))
    q = st.chat_input("Pose une question sur un match, une équipe, un championnat…") or q_ex
    if q:
        st.session_state.chat.append({"role": "user", "content": q})
        local = A.repondre(q)
        texte = (A.reformuler(q, local, st.session_state.chat, cle) if cle else None) or local["texte"]
        st.session_state.chat.append({"role": "assistant", "content": texte, "liens": local["liens"]})
        st.session_state.chat = st.session_state.chat[-20:]
        st.rerun()
    if st.session_state.chat and st.button("Effacer la conversation"):
        st.session_state.chat = []; st.rerun()


# ================================================================ Méthode
def methode():
    styles(); bandeau(); st.markdown("### Méthode, sources et limites")
    p = tout()["performance"] or {}
    st.markdown(f"""
**Goalgebra** est un projet académique d'analyse statistique du football : il estime des **probabilités** pour les matchs à venir
et mesure honnêtement leur fiabilité. Ce n'est pas un outil de pari.

#### 1. Données
- **Historique** : dataset public *Club Football Match Data* (xgabora, 2000 → aujourd'hui) — résultats, tirs, corners, cartons, cotes, Elo ClubElo.
- **Matchs du jour** : football-data.org (clé gratuite, scores en direct), football-data.co.uk (résultats, calendrier, cotes),
  openfootball (calendrier complet, secours sans clé). Si une source ne répond pas, la suivante prend le relais.
- **Coupes d'Europe** : openfootball/champions-league (Ligue des champions, Ligue Europa, Conference League).
- Les données sont recalculées toutes les 2 heures par GitHub Actions (en secours, par l'application au-delà de 6 heures). Un bandeau signale tout retard des sources.
- **Journal honnête** : une prédiction n'est publiée et figée qu'avant le coup d'envoi ; elle n'est jamais modifiée ensuite.

#### 2. Modèle v5 (5 grands championnats)
- **Résultat 1X2** : régression logistique multinomiale sur des variables d'avant-match : écart d'Elo, pi-ratings, forme en **xG approché**
  (tirs cadrés × taux de conversion de la ligue), ratings offensifs/défensifs, et **motivation** de fin de saison (course au titre, maintien, absence d'enjeu).
- **Buts et scores** : Poisson avec correction de Dixon-Coles → score exact, plus/moins de buts, les deux équipes marquent.
- **Corners et cartons** : modèles de comptage dédiés.
- **Promus** : leur forme en deuxième division est prise en compte.
- **Coupes d'Europe** : modèle séparé fondé sur l'Elo (comparable entre pays), confiance plafonnée au niveau B.

#### 3. Évaluation
- **Rétrospective (2021/22 → 2025/26, walk-forward)** : chaque saison est prédite par un modèle entraîné uniquement sur les saisons
  précédentes, et tous les modèles sont comparés sur les mêmes 8 896 matchs. Les variables d'enjeu de v5 ayant été étudiées sur
  2010-2025, cette période n'est plus un test totalement intact pour v5.
- **Prospective (2026/27 →)** : le journal des prédictions figées avant chaque coup d'envoi, jamais utilisé pour choisir le modèle.
Sur la période affichée : **{P(p.get("accuracy"))}** de bonnes issues, log loss **{_f(3)(p.get("logLoss"))}**
(cotes des bookmakers : {_f(3)((p.get("market") or {}).get("logLoss"))}), calibration ECE **{_f(3)(p.get("ece"))}**.
Le modèle est bien calibré mais **ne bat pas les cotes** en moyenne : elles intègrent compositions, blessures et informations de dernière minute.

#### 4. Sélection du jour et abstention
Pour chaque match, 17 marchés sont dérivés d'une même distribution des scores (cohérents entre eux). Chacun reçoit une probabilité
calibrée, une **borne basse** (incertitude du calibrage + désaccord entre modèles) et une **référence** (marché sans marge si coté,
sinon fréquence historique). Une sélection n'est **retenue** que si même sa borne basse dépasse la référence et un seuil appris sur la
validation 2021-2024 ; sinon **analyse prudente** ou **abstention**. Sur le test réservé 2025/26 : 59 % de matchs retenus, 88 % de
réussite pour 87 % annoncés. Toujours lire la réussite avec la couverture.

#### 5. Degré de confiance A / B / C
Il combine l'écart avec les cotes, l'avancement de la saison et la netteté du favori. Pour chaque prédiction, l'application affiche
la fréquence **réellement observée** dans les matchs passés du même niveau, avec un intervalle de confiance de Wilson à 95 %.

#### 6. Ce que le modèle ne sait pas
Compositions d'équipe, blessures, suspensions, météo, changements d'entraîneur, enjeux extra-sportifs. Les probabilités restent
des fréquences de long terme : un favori à 70 % perd environ 3 fois sur 10.

#### 7. Références
Dixon & Coles (1997) · Constantinou & Fenton (2013, pi-ratings) · Hvattum & Arntzen (2010, Elo) · Hassard & Kerr (2024) ·
Ren & Susnjak (2022) · Sallis, Georgoulas & Tsoulos (2026). Détails : `docs/methodologie.md`, `docs/resultats.md`, `docs/references.md`.
""")
    st.info("Pour entraîner et tester le modèle soi-même (prédire un match, une journée, voir les formules), ouvrir **Étude → Laboratoire du modèle**.")


def P(x):
    return pct(x, 1)


def _perf_selection():
    """Sélection du jour : test final réservé (artefact) et suivi prospectif (journal, sélections figées avant le coup d'envoi)."""
    from .selection import DECISION, artefact
    art = artefact()
    t = art.get("test_T")
    if not t:
        return
    st.markdown("#### Sélection du jour · fiabilité")
    rows = [{"Décision": DECISION[k][0], "Part des matchs": v["couverture"], "Réussite observée": v["reussite"], "Probabilité annoncée": v["annonce"], "Matchs": v["n"]}
            for k, v in t.items() if isinstance(v, dict)]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={k: st.column_config.NumberColumn(format="percent") for k in ("Part des matchs", "Réussite observée", "Probabilité annoncée")})
    st.caption(f"Test final réservé {t.get('saison')} ({t.get('matchs')} matchs), jamais utilisé pour choisir les seuils. Pour les abstentions : "
               "réussite qu'aurait eue la sélection la plus probable, souvent triviale (ex. plus de 0,5 but), donc sans information. "
               "Toujours lire la réussite avec la part des matchs couverts.")
    J = [v["selection"] for v in (tout().get("journal") or {}).values() if v.get("selection") and v["selection"].get("resultat") is not None]
    if J:
        df = pd.DataFrame([{"décision": x["decision"], "réussie": x["resultat"], "p": (x.get("choix") or {}).get("p")} for x in J])
        agg = df.groupby("décision").agg(sélections=("réussie", "size"), réussite=("réussie", "mean"), annoncé=("p", "mean"))
        st.markdown("**Suivi prospectif** (sélections figées avant le coup d'envoi, saison en cours)")
        st.dataframe(agg, width="stretch", column_config={k: st.column_config.NumberColumn(format="percent") for k in ("réussite", "annoncé")})
    else:
        st.caption("Suivi prospectif : aucune sélection figée n'a encore de résultat.")
