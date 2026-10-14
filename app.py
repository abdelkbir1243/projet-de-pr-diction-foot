"""Goalgebra — application Streamlit (même interface que le site web).

Lit les données publiées dans web/data/*.json et les recalcule elle-même en arrière-plan quand elles ont plus de 3 heures
(appui/donnees.py). La page « Laboratoire du modèle » conserve l'application d'étude (entraînement et évaluation à la volée).
"""
import streamlit as st

st.set_page_config(page_title="Goalgebra — analyse statistique du football", page_icon="⚽", layout="wide",
                   initial_sidebar_state="collapsed", menu_items={"About": "Goalgebra · projet académique d'analyse statistique du football. "
                                                                           "Probabilités, jamais des certitudes ; aucun conseil de pari."})

from appui import compte, pages, selection  # noqa: E402

u = compte.utilisateur()                                     # mode plateforme : session restaurée depuis le cookie
page_compte = st.Page(compte.page_compte, title=("Mon compte" if u else "Connexion"), icon="👤", url_path="compte")
if compte.prive() and not u:                                 # plateforme privée : seule la page de connexion est accessible
    nav = st.navigation([page_compte], position="top")
else:
    menus = {
        "Goalgebra": [
            st.Page(selection.page, title="Sélection du jour", icon="🎯", default=True),
            st.Page(pages.accueil, title="Matchs", icon="🏟️", url_path="matchs"),
            st.Page(pages.predictions, title="Prédictions IA", icon="✨", url_path="predictions"),
            st.Page(pages.equipes, title="Équipes", icon="🛡️", url_path="equipes"),
            st.Page(pages.competitions, title="Compétitions", icon="🏆", url_path="competitions"),
            st.Page(pages.cotes, title="Cotes & risque", icon="⚖️", url_path="cotes"),
            st.Page(pages.assistant, title="Assistant", icon="💬", url_path="assistant"),
            st.Page(pages.performance, title="Performance de l'IA", icon="📈", url_path="performance"),
            st.Page(pages.page_match, title="Fiche match", icon="📊", url_path="match"),
        ],
        "Étude": [st.Page(pages.methode, title="Méthode et limites", icon="📘", url_path="methode")]
        # le Laboratoire réentraîne le modèle (~1 Go de mémoire) : réservé aux administrateurs sur un serveur
        + ([st.Page("appui/laboratoire.py", title="Laboratoire du modèle", icon="🧪", url_path="laboratoire")]
           if not compte.plateforme_active() or compte.est_admin() else []),
    }
    if compte.plateforme_active():
        menus["Compte"] = [page_compte] + ([st.Page(compte.page_admin, title="Administration", icon="🛠️", url_path="admin")]
                                           if compte.est_admin() else [])
    nav = st.navigation(menus, position="top")
nav.run()

st.markdown('<div style="margin-top:32px;padding:14px 0;border-top:1px solid #e5e7eb;font-size:12px;color:#94a3b8;text-align:center">'
            "Goalgebra · projet académique · probabilités statistiques, jamais des résultats garantis · aucun conseil de pari · "
            "données : football-data.co.uk, football-data.org, openfootball, ClubElo</div>", unsafe_allow_html=True)
