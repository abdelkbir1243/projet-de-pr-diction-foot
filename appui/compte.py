"""Comptes dans l'application Streamlit : connexion, inscription, équipes suivies, clés d'API, administration.

Actif seulement en mode plateforme (variable GOALGEBRA_PLATEFORME=1, base de données configurée). La session est conservée
entre les rechargements par un cookie « gg_session » : jeton aléatoire dont seule l'empreinte est en base (révocable, 14 jours).
Connexion déléguée facultative (Google ou tout fournisseur OIDC) via st.login si la section [auth] est configurée.
"""
import json
import os
import threading
from datetime import timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from .ui import carte, e, html_, styles, tuile

COOKIE = "gg_session"


def plateforme_active() -> bool:
    return os.environ.get("GOALGEBRA_PLATEFORME", "0") == "1"


def prive() -> bool:
    return plateforme_active() and os.environ.get("PLATEFORME_PRIVEE", "0") == "1"


def inscriptions_ouvertes() -> bool:
    return os.environ.get("INSCRIPTIONS_OUVERTES", "1") == "1"


def _cookie(valeur: str, age: int):
    """Écrit le cookie de session dans la page (le jeton est généré par nous : url-safe, jamais issu d'une saisie)."""
    secure = "; Secure" if os.environ.get("COOKIE_SECURE", "1") == "1" else ""
    code = f"<script>parent.document.cookie = {json.dumps(f'{COOKIE}={valeur}; Max-Age={age}; Path=/; SameSite=Strict{secure}')};</script>"
    if hasattr(st, "iframe"):
        st.iframe(code, height=1)
    else:                                                    # Streamlit < 1.52
        components.html(code, height=0)


def oidc_configure() -> bool:
    try:
        return "auth" in st.secrets
    except Exception:
        return False


def utilisateur() -> dict | None:
    """Utilisateur connecté (dict) ou None. Restaure la session depuis le cookie au premier affichage."""
    if not plateforme_active():
        return None
    if "gg_user" in st.session_state:
        return st.session_state["gg_user"]
    from plateforme import comptes as K
    u = None
    try:
        u = K.utilisateur_de_session(st.context.cookies.get(COOKIE))
        if not u and oidc_configure() and getattr(st.user, "is_logged_in", False) and st.user.get("email"):
            u = K.utilisateur_par_email(st.user.get("email"), creer=inscriptions_ouvertes(), nom=st.user.get("name", ""))
    except Exception as ex:                                  # base indisponible : l'application reste consultable
        st.session_state["gg_erreur_db"] = str(ex)[:200]
    st.session_state["gg_user"] = _dict(u) if u else None
    return st.session_state["gg_user"]


def _dict(u) -> dict:
    return {"id": u.id, "email": u.email, "nom": u.nom, "role": u.role}


def est_admin() -> bool:
    u = utilisateur()
    return bool(u and u["role"] == "admin")


def _connecter(u):
    from plateforme import comptes as K
    jeton = K.ouvrir_session(u.id)
    st.session_state["gg_user"] = _dict(u)
    st.session_state["gg_cookie"] = jeton


def deconnecter():
    from plateforme import comptes as K
    K.fermer_session(st.context.cookies.get(COOKIE) or st.session_state.get("gg_cookie"))
    st.session_state["gg_user"] = None
    st.session_state["gg_logout"] = True
    st.session_state.pop("gg_cookie", None)


def poser_cookie():
    """À appeler à chaque page : écrit ou efface le cookie après une connexion / déconnexion."""
    if st.session_state.pop("gg_logout", False):
        _cookie("", 0)
    jeton = st.session_state.pop("gg_cookie", None)
    if jeton:
        _cookie(jeton, int(timedelta(days=14).total_seconds()))


# ================================================================ page « Mon compte »
def page_compte():
    from plateforme import comptes as K
    styles(); poser_cookie()
    u = utilisateur()
    if st.session_state.get("gg_erreur_db"):
        st.error("Base de données indisponible : la connexion est momentanément impossible.")
        return
    if not u:
        st.markdown("### Connexion")
        if oidc_configure():
            if st.button("Se connecter avec Google", icon=":material/login:", width="stretch"):
                st.login()
            st.caption("ou avec une adresse e-mail :")
        onglets = st.tabs(["Se connecter", "Créer un compte"] if inscriptions_ouvertes() else ["Se connecter"])
        with onglets[0]:
            with st.form("connexion"):
                email = st.text_input("Adresse e-mail", autocomplete="email")
                mdp = st.text_input("Mot de passe", type="password", autocomplete="current-password")
                if st.form_submit_button("Se connecter", type="primary", width="stretch"):
                    try:
                        _connecter(K.authentifier(email, mdp)); st.rerun()
                    except K.ErreurCompte as ex:
                        st.error(str(ex))
        if inscriptions_ouvertes():
            with onglets[1]:
                with st.form("inscription"):
                    nom = st.text_input("Nom (facultatif)", max_chars=80)
                    email = st.text_input("Adresse e-mail", autocomplete="email", key="ins_email")
                    mdp = st.text_input("Mot de passe (10 caractères minimum, une lettre et un chiffre)", type="password", autocomplete="new-password")
                    mdp2 = st.text_input("Confirmer le mot de passe", type="password", autocomplete="new-password")
                    ok = st.checkbox("J'ai compris que Goalgebra publie des probabilités statistiques, pas des conseils de pari (18+).")
                    if st.form_submit_button("Créer mon compte", type="primary", width="stretch"):
                        try:
                            if mdp != mdp2:
                                raise K.ErreurCompte("Les deux mots de passe sont différents.")
                            if not ok:
                                raise K.ErreurCompte("Merci de cocher la case de confirmation.")
                            K.creer_utilisateur(email, mdp, nom)
                            _connecter(K.authentifier(email, mdp)); st.rerun()
                        except K.ErreurCompte as ex:
                            st.error(str(ex))
        return

    st.markdown(f"### Mon compte · {e(u['nom'] or u['email'])}")
    c1, c2 = st.columns([4, 1], vertical_alignment="center")
    c1.caption(f"{u['email']} · rôle : {u['role']}")
    if c2.button("Se déconnecter", width="stretch"):
        deconnecter()
        if oidc_configure() and getattr(st.user, "is_logged_in", False):
            st.logout()
        st.rerun()
    t1, t2, t3 = st.tabs(["Équipes suivies", "Clés d'API", "Sécurité"])
    with t1:
        from .donnees import tout
        d = tout()
        fav = K.favoris(u["id"])
        if not fav:
            st.info("Aucune équipe suivie. Ouvre une fiche équipe (menu Équipes) et clique sur « Suivre ».")
        for sl in fav:
            t = d["teams"].get(sl) or d["index"].get(sl) or {"name": sl}
            a, b = st.columns([5, 1], vertical_alignment="center")
            a.markdown(f'<a href="equipes?t={e(sl)}" target="_self">{e(t["name"])}</a>', unsafe_allow_html=True)
            if b.button("Ne plus suivre", key=f"nf_{sl}"):
                K.basculer_favori(u["id"], sl); st.rerun()
    with t2:
        base = os.environ.get("API_URL_PUBLIQUE", "https://api.example.org")
        st.markdown(f"L'API publique renvoie les matchs, prédictions, équipes et classements au format JSON. "
                    f"Documentation : [{base}/docs]({base}/docs). Envoie la clé dans l'en-tête `X-API-Key`.")
        with st.form("nouvelle_cle", clear_on_submit=True):
            nom = st.text_input("Nom de la clé (ex. « projet de cours »)", max_chars=60)
            if st.form_submit_button("Créer une clé"):
                try:
                    st.session_state["gg_cle_neuve"] = K.creer_cle(u["id"], nom)
                except K.ErreurCompte as ex:
                    st.error(str(ex))
        neuve = st.session_state.pop("gg_cle_neuve", None)
        if neuve:
            st.success("Clé créée. Copie-la maintenant : elle ne sera plus jamais affichée.")
            st.code(neuve, language=None)
            st.code(f'curl -H "X-API-Key: {neuve}" {base}/v1/predictions/upcoming', language="bash")
        ks = K.cles(u["id"])
        for k in ks:
            a, b = st.columns([5, 1], vertical_alignment="center")
            etat = "révoquée" if k.revoquee else f"quota {k.quota_jour}/jour"
            a.markdown(f"`{k.prefixe}…` · {e(k.nom or 'sans nom')} · {etat} · créée le {k.cree_le:%d/%m/%Y}"
                       + (f" · utilisée le {k.derniere_utilisation:%d/%m/%Y %H:%M}" if k.derniere_utilisation else ""))
            if not k.revoquee and b.button("Révoquer", key=f"rv_{k.id}"):
                K.revoquer_cle(u["id"], k.id); st.rerun()
    with t3:
        with st.form("mdp", clear_on_submit=True):
            ancien = st.text_input("Mot de passe actuel", type="password")
            nouveau = st.text_input("Nouveau mot de passe", type="password")
            if st.form_submit_button("Changer le mot de passe"):
                try:
                    K.changer_mdp(u["id"], ancien, nouveau)
                    st.success("Mot de passe changé. Les autres sessions ont été fermées.")
                    _connecter(K.authentifier(u["email"], nouveau))
                except K.ErreurCompte as ex:
                    st.error(str(ex))
        if st.button("Se déconnecter de tous les appareils"):
            K.fermer_toutes_sessions(u["id"]); deconnecter(); st.rerun()


# ================================================================ suivre une équipe (page Équipes)
def bouton_suivre(slug: str):
    u = utilisateur()
    if not u:
        if plateforme_active():
            st.caption("Connecte-toi (menu Mon compte) pour suivre cette équipe.")
        return
    from plateforme import comptes as K
    suivie = slug in K.favoris(u["id"])
    if st.button("★ Suivie" if suivie else "☆ Suivre", key=f"suivre_{slug}", type="secondary" if suivie else "primary"):
        K.basculer_favori(u["id"], slug); st.rerun()


def favoris_courants() -> list[str]:
    u = utilisateur()
    if not u:
        return []
    from plateforme import comptes as K
    try:
        return K.favoris(u["id"])
    except Exception:
        return []


# ================================================================ administration
def _lancer_cycle():
    from plateforme import worker
    if st.session_state.get("_cycle") and st.session_state["_cycle"].is_alive():
        return False
    f = threading.Thread(target=worker.cycle, daemon=True)
    f.start(); st.session_state["_cycle"] = f
    return True


def page_admin():
    styles(); poser_cookie()
    if not est_admin():
        st.error("Accès réservé aux administrateurs."); return
    from sqlalchemy import func, select
    from plateforme import comptes as K
    from plateforme.db import CleApi, ExecutionPipeline, Prediction, UsageApi, Utilisateur, maintenant, session
    st.markdown("### Administration")
    with session() as s:
        n_u = s.scalar(select(func.count()).select_from(Utilisateur)) or 0
        n_k = s.scalar(select(func.count()).select_from(CleApi).where(CleApi.revoquee.is_(False))) or 0
        req = s.scalar(select(func.coalesce(func.sum(UsageApi.requetes), 0)).where(UsageApi.jour == maintenant().date().isoformat())) or 0
        runs = list(s.scalars(select(ExecutionPipeline).order_by(ExecutionPipeline.debut.desc()).limit(50)))
        preds = list(s.scalars(select(Prediction).where(Prediction.resultat.is_not(None))))
        n_p = s.scalar(select(func.count()).select_from(Prediction)) or 0
    der = runs[0] if runs else None
    etat = "—" if not der else {"succes": "✅ succès", "echec": "❌ échec", "en_cours": "⏳ en cours"}.get(der.statut, der.statut)
    html_('<div class="gg-tiles" style="padding:0">' + tuile("Comptes", n_u) + tuile("Clés d'API actives", n_k) + tuile("Requêtes API aujourd'hui", req)
          + tuile("Dernier calcul", etat, f"{der.debut:%d/%m %H:%M}" if der else "") + tuile("Journal", n_p, f"{len(preds)} avec résultat") + "</div>")
    t1, t2, t3, t4, t5 = st.tabs(["Calculs", "Journal prospectif", "Utilisateurs", "API", "Audit"])
    with t1:
        if st.button("Lancer un calcul maintenant", type="primary"):
            st.toast("Calcul lancé (3 à 8 min)." if _lancer_cycle() else "Un calcul est déjà en cours.")
        st.dataframe(pd.DataFrame([{"Début": r.debut, "Fin": r.fin, "Statut": r.statut, "Mode": r.mode, "Matchs": r.matchs,
                                    "Dernier résultat": r.dernier_resultat, "En retard": r.en_retard, "Message": r.message} for r in runs]),
                     hide_index=True, width="stretch")
    with t2:
        if not preds:
            st.info("Aucune prédiction du journal n'a encore de résultat.")
        else:
            import numpy as np
            P = np.array([[p.p_dom, p.p_nul, p.p_ext] for p in preds]); y = np.array(["HDA".index(p.resultat) for p in preds])
            ll = -np.log(np.clip(P[np.arange(len(y)), y], 1e-12, 1)).mean()
            acc = (P.argmax(1) == y).mean()
            html_('<div class="gg-tiles" style="padding:0">' + tuile("Matchs évalués", len(y)) + tuile("Bon résultat", f"{100 * acc:.1f} %")
                  + tuile("Log loss", f"{ll:.3f}", "1,099 = hasard uniforme") + "</div>")
            st.caption("Évaluation prospective : prédictions figées avant le coup d'envoi, jamais utilisées pour choisir le modèle.")
    with t3:
        us = K.utilisateurs()
        st.dataframe(pd.DataFrame([{"id": x.id, "E-mail": x.email, "Nom": x.nom, "Rôle": x.role, "Actif": x.actif, "Créé le": x.cree_le,
                                    "Dernière connexion": x.derniere_connexion} for x in us]), hide_index=True, width="stretch")
        if us:
            cible = st.selectbox("Compte", us, format_func=lambda x: f"{x.email} ({x.role}{'' if x.actif else ', désactivé'})")
            a, b = st.columns(2)
            moi = utilisateur()["email"]
            if a.button("Activer / désactiver", disabled=cible.email == moi):
                K.modifier_utilisateur(cible.id, moi, actif=not cible.actif)
                if cible.actif:
                    K.fermer_toutes_sessions(cible.id)
                st.rerun()
            if b.button("Passer admin / utilisateur", disabled=cible.email == moi):
                K.modifier_utilisateur(cible.id, moi, role="user" if cible.role == "admin" else "admin"); st.rerun()
    with t4:
        rows = K.usage_api()
        st.dataframe(pd.DataFrame(rows, columns=["Jour", "Clé", "Compte", "Requêtes"]), hide_index=True, width="stretch")
    with t5:
        st.dataframe(pd.DataFrame([{"Le": a.le, "Acteur": a.acteur, "Action": a.action, "Détail": a.detail} for a in K.journal_audit()]),
                     hide_index=True, width="stretch")
