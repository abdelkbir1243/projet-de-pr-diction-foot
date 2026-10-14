"""Composants visuels de l'application (même identité que le site Goalgebra) : styles, écussons, barres de probabilités,
cartes de match, niveaux de confiance. Tout est du HTML/CSS injecté, sans ressource externe autre qu'une police Google."""
import html

import streamlit as st

from datetime import datetime, timedelta

from .donnees import equipe, heure, maintenant


def _passe(m: dict) -> bool:
    try:
        return datetime.fromisoformat(m["kickoff"].replace("Z", "+00:00")) + timedelta(hours=2, minutes=15) < maintenant()
    except (KeyError, ValueError):
        return False

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root{--brand:#4f46e5;--brand2:#7c3aed;--soft:#eef0ff;--ink:#3730a3;--txt:#0f172a;--t2:#475569;--t3:#94a3b8;--bd:#e5e7eb;--s2:#f6f7f9;
--home:#2a78d6;--draw:#9ca3af;--away:#eb6834;--good:#16803c;--goods:#e8f5ec;--warn:#b45309;--warns:#fef3c7;--bad:#d92d20;--bads:#fee4e2;--live:#e11d48}
html,body,[class*="css"],.stMarkdown,.stButton button{font-family:Inter,system-ui,sans-serif}
.block-container,[data-testid="stMainBlockContainer"]{padding-top:4.5rem!important;max-width:1200px}
.gg-card ul{padding-left:30px}
h1,h2,h3{letter-spacing:-.01em}
.gg-card{background:#fff;border:1px solid var(--bd);border-radius:14px;box-shadow:0 1px 2px rgba(16,24,40,.04);overflow:hidden;margin-bottom:12px}
.gg-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:10px 14px;border-bottom:1px solid var(--bd)}
.gg-title{font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--t2)}
.gg-sub{font-size:12px;color:var(--t3)}
.gg-cc{display:inline-grid;place-items:center;width:30px;height:20px;border-radius:5px;background:#111827;color:#fff;font:700 9px ui-monospace,monospace}
.gg-row{display:grid;grid-template-columns:58px minmax(0,1fr) 190px;gap:12px;align-items:center;padding:10px 14px;border-top:1px solid var(--bd);
 text-decoration:none!important;color:inherit!important;transition:background .15s}
.gg-row:first-of-type{border-top:0}.gg-row:hover{background:#f8f9ff}
.gg-team{display:flex;align-items:center;gap:8px;font-size:14px;font-weight:500;color:var(--txt);min-width:0}
.gg-team span.n{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.gg-team .sc{margin-left:auto;font-weight:700;font-variant-numeric:tabular-nums}
.gg-time{font-weight:600;font-size:13px;font-variant-numeric:tabular-nums;color:var(--txt)}
.gg-pill{display:inline-flex;align-items:center;gap:4px;border-radius:6px;padding:1px 6px;font-size:10px;font-weight:700;letter-spacing:.03em;text-transform:uppercase}
.gg-ai{background:var(--soft);color:var(--ink)} .gg-A{background:var(--goods);color:var(--good)} .gg-B{background:var(--warns);color:var(--warn)}
.gg-C{background:var(--bads);color:var(--bad)} .gg-ft{background:var(--s2);color:var(--t3)} .gg-live{background:#ffe4e6;color:var(--live)}
.gg-bar{display:flex;height:7px;border-radius:99px;overflow:hidden;gap:2px}
.gg-bar i{display:block;height:100%}
.gg-nums{display:flex;justify-content:space-between;font-size:11px;color:var(--t3);margin-top:3px;font-variant-numeric:tabular-nums}
.gg-nums b{color:var(--txt)}
.gg-big{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:6px}
.gg-big div{font-size:28px;font-weight:600;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.gg-big small{display:block;font-size:11px;font-weight:500;letter-spacing:.06em;text-transform:uppercase;color:var(--t3)}
.gg-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;padding:12px 14px}
.gg-tile{border:1px solid var(--bd);border-radius:12px;padding:10px 12px;background:#fff}
.gg-tile .l{font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.05em;color:var(--t3)}
.gg-tile .v{font-size:20px;font-weight:600;font-variant-numeric:tabular-nums}.gg-tile .s{font-size:11px;color:var(--t2)}
.gg-hero{position:relative;padding:22px 18px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:10px;text-align:center}
.gg-hero .nm{font-size:18px;font-weight:600;margin-top:6px}.gg-hero .mid{font-size:30px;font-weight:700;font-variant-numeric:tabular-nums}
.gg-band{height:3px;background:linear-gradient(90deg,var(--brand),var(--brand2))}
.gg-note{font-size:11px;color:var(--t3);padding:8px 14px;border-top:1px solid var(--bd);line-height:1.5}
.gg-list{padding:4px 14px 10px;font-size:13px;color:var(--t2)} .gg-list li{margin:3px 0}
.gg-banner{border:1px solid var(--bd);background:#fff;border-radius:10px;padding:6px 12px;font-size:12px;color:var(--t2);margin-bottom:10px}
@media (max-width:640px){.gg-row{grid-template-columns:48px minmax(0,1fr)}.gg-row .p{grid-column:2}.gg-hero .nm{font-size:15px}}
</style>
"""


def styles():
    st.markdown(CSS, unsafe_allow_html=True)


def e(x) -> str:
    return html.escape(str(x))


def ecusson(slug: str | None, taille: int = 22) -> str:
    t = equipe(slug)
    c = e(t["code"] if taille >= 22 else t["code"][:1])
    return (f'<svg width="{taille}" height="{taille}" viewBox="0 0 32 36" aria-hidden="true" style="flex:none">'
            f'<path d="M16 1 30 6v11c0 9-6 15-14 18C8 32 2 26 2 17V6z" fill="{e(t["color"])}"/>'
            f'<text x="16" y="21" text-anchor="middle" font-family="Inter,sans-serif" font-weight="700" font-size="{9 if len(c) > 2 else 12}" fill="#fff">{c}</text></svg>')


def barre(p_h, p_d, p_a, gros=False, libelles=None) -> str:
    seg = "".join(f'<i style="width:{100 * p:.1f}%;background:var(--{k});opacity:{1 if p == max(p_h, p_d, p_a) else .45}"></i>'
                  for p, k in ((p_h, "home"), (p_d, "draw"), (p_a, "away")))
    if gros:
        l = libelles or ("Domicile", "Nul", "Extérieur")
        tete = "".join(f'<div style="text-align:{a}">{round(100 * p)}<span style="font-size:14px">%</span><small>{e(n)}</small></div>'
                       for p, n, a in ((p_h, l[0], "left"), (p_d, l[1], "center"), (p_a, l[2], "right")))
        return f'<div class="gg-big">{tete}</div><div class="gg-bar" style="height:10px">{seg}</div>'
    nums = "".join(f'<{"b" if p == max(p_h, p_d, p_a) else "span"}>{round(100 * p)}</{"b" if p == max(p_h, p_d, p_a) else "span"}>'
                   for p in (p_h, p_d, p_a))
    return f'<div class="gg-bar">{seg}</div><div class="gg-nums">{nums}</div>'


def niveau(lv: str | None, long=False) -> str:
    if not lv:
        return ""
    txt = {"A": "Confiance élevée", "B": "Confiance moyenne", "C": "Confiance faible"}[lv] if long else lv
    return f'<span class="gg-pill gg-{lv}">🛡 {txt}</span>'


def statut(m: dict) -> str:
    s = m["status"]
    if s in ("live", "halftime"):
        return f'<span class="gg-pill gg-live">● {m.get("minute") or "LIVE"}\'</span>'
    if s == "finished":
        return '<span class="gg-pill gg-ft">Terminé</span>'
    if s == "postponed":
        return '<span class="gg-pill gg-B">Reporté</span>'
    if s == "cancelled":
        return '<span class="gg-pill gg-ft">Annulé</span>'
    if s == "scheduled" and m.get("started") and not (m.get("awaitingResult") or _passe(m)):
        return f'<span class="gg-time">{heure(m)}</span><br><span class="gg-pill gg-live" title="Coup d\'envoi passé, score en direct indisponible">commencé</span>'
    if s == "scheduled" and (m.get("awaitingResult") or _passe(m)):
        return f'<span class="gg-time">{heure(m)}</span><br><span class="gg-pill gg-ft" title="Match joué, score pas encore publié par les sources gratuites">score à venir</span>'
    return f'<span class="gg-time">{heure(m)}</span>'


def ligne_match(m: dict) -> str:
    p = m.get("prediction")
    sc = m.get("score") if m["status"] in ("finished", "live", "halftime") else None
    eq = "".join(f'<div class="gg-team">{ecusson(s)}<span class="n">{e(n)}</span>{f"<span class=sc>{g}</span>" if sc else ""}</div>'
                 for s, n, g in ((m["home"], m["homeName"], (sc or {}).get("home")), (m["away"], m["awayName"], (sc or {}).get("away"))))
    droite = ""
    if p:
        lv = (p.get("trust") or {}).get("level")
        droite = (f'<div class="p"><div style="display:flex;justify-content:space-between;margin-bottom:4px"><span class="gg-pill gg-ai">✦ IA</span>{niveau(lv)}</div>'
                  f'{barre(p["home"], p["draw"], p["away"])}</div>')
    else:
        droite = '<div class="p gg-sub">Prédiction indisponible</div>'
    return f'<a class="gg-row" href="match?m={e(m["slug"])}" target="_self"><div>{statut(m)}</div><div style="display:grid;gap:6px;min-width:0">{eq}</div>{droite}</a>'


def carte(titre: str, corps: str, sous_titre: str = "", droite: str = "", note: str = "", bande=False) -> str:
    tete = (f'<div class="gg-head"><div><div class="gg-title">{titre}</div>{f"<div class=gg-sub>{sous_titre}</div>" if sous_titre else ""}</div>'
            f'<div>{droite}</div></div>')
    return f'<div class="gg-card">{"<div class=gg-band></div>" if bande else ""}{tete}{corps}{f"<div class=gg-note>{note}</div>" if note else ""}</div>'


def tuile(label, valeur, sous="") -> str:
    return f'<div class="gg-tile"><div class="l">{e(label)}</div><div class="v">{valeur}</div>{f"<div class=s>{sous}</div>" if sous else ""}</div>'


def pct(x, d=0) -> str:
    return "—" if x is None else f"{100 * x:.{d}f} %".replace(".", ",")


def html_(x: str):
    st.markdown(x, unsafe_allow_html=True)
