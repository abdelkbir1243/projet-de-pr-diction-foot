"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

const fr = {
  "nav.matches": "Matchs", "nav.competitions": "Compétitions", "nav.predictions": "Prédictions IA", "nav.stats": "Statistiques",
  "nav.teams": "Équipes", "nav.performance": "Performance IA", "nav.standings": "Classements", "nav.home": "Accueil", "nav.ai": "IA",
  "nav.profile": "Profil", "nav.favorites": "Favoris", "nav.markets": "Cotes & risque", "nav.assistant": "Assistant",
  "search.placeholder": "Équipe, compétition, joueur, match…", "search.empty": "Aucun résultat.", "search.teams": "Équipes",
  "search.competitions": "Compétitions", "search.matches": "Matchs", "search.players": "Joueurs",
  "search.playersNA": "Les données joueurs ne sont pas encore connectées.",
  "date.yesterday": "Hier", "date.today": "Aujourd'hui", "date.tomorrow": "Demain", "date.pick": "Choisir une date",
  "filter.all": "Tous", "filter.live": "En direct", "filter.upcoming": "À venir", "filter.finished": "Terminés", "filter.predicted": "AI Predictions",
  "status.scheduled": "À venir", "status.live": "En direct", "status.halftime": "Mi-temps", "status.finished": "Terminé",
  "status.postponed": "Reporté", "status.cancelled": "Annulé",
  "match.prediction": "Prédiction IA", "match.noPrediction": "Prédiction indisponible", "match.draw": "Nul",
  "match.confidence": "Indice de confiance", "match.likelyScore": "Score le plus probable", "match.xg": "Buts attendus",
  "empty.noMatches": "Aucun match ce jour-là", "empty.noMatchesHint": "Essayez une autre date ou retirez les filtres.",
  "empty.filter": "Aucun match ne correspond à ce filtre.",
  "demo.banner": "Mode démonstration : les affiches et scores des prochains jours sont simulés. Équipes, statistiques, classements et performances du modèle sont réels.",
  "live.banner": "Données en temps réel",
  "sidebar.competitions": "Compétitions", "sidebar.topTeams": "Top équipes (Elo)", "sidebar.trending": "Matchs à suivre",
  "sidebar.noFavorites": "Ajoutez des équipes en favoris avec ⭐",
  "header.login": "Connexion", "header.notifications": "Notifications", "header.theme": "Thème", "header.lang": "Langue",
  "disclaimer": "Probabilités statistiques, jamais des résultats garantis. Plateforme d'analyse, pas de paris.",
  "tabs.overview": "Aperçu", "tabs.prediction": "Analyse IA", "tabs.stats": "Stats", "tabs.h2h": "H2H", "tabs.lineups": "Compos",
  "tabs.standings": "Classement",
};
type Dict = typeof fr;
const en: Dict = {
  "nav.matches": "Matches", "nav.competitions": "Competitions", "nav.predictions": "AI Predictions", "nav.stats": "Statistics",
  "nav.teams": "Teams", "nav.performance": "AI Performance", "nav.standings": "Standings", "nav.home": "Home", "nav.ai": "AI",
  "nav.profile": "Profile", "nav.favorites": "Favourites", "nav.markets": "Odds & risk", "nav.assistant": "Assistant",
  "search.placeholder": "Team, competition, player, match…", "search.empty": "No results.", "search.teams": "Teams",
  "search.competitions": "Competitions", "search.matches": "Matches", "search.players": "Players",
  "search.playersNA": "Player data is not connected yet.",
  "date.yesterday": "Yesterday", "date.today": "Today", "date.tomorrow": "Tomorrow", "date.pick": "Pick a date",
  "filter.all": "All", "filter.live": "Live", "filter.upcoming": "Upcoming", "filter.finished": "Finished", "filter.predicted": "AI Predictions",
  "status.scheduled": "Upcoming", "status.live": "Live", "status.halftime": "Half-time", "status.finished": "Full-time",
  "status.postponed": "Postponed", "status.cancelled": "Cancelled",
  "match.prediction": "AI prediction", "match.noPrediction": "Prediction unavailable", "match.draw": "Draw",
  "match.confidence": "Confidence index", "match.likelyScore": "Most likely score", "match.xg": "Expected goals",
  "empty.noMatches": "No matches on this day", "empty.noMatchesHint": "Try another date or clear the filters.",
  "empty.filter": "No match matches this filter.",
  "demo.banner": "Demo mode: upcoming fixtures and scores are simulated. Teams, statistics, standings and model performance are real.",
  "live.banner": "Real-time data",
  "sidebar.competitions": "Competitions", "sidebar.topTeams": "Top teams (Elo)", "sidebar.trending": "Matches to watch",
  "sidebar.noFavorites": "Add favourite teams with ⭐",
  "header.login": "Sign in", "header.notifications": "Notifications", "header.theme": "Theme", "header.lang": "Language",
  "disclaimer": "Statistical probabilities, never guaranteed outcomes. An analytics platform, not a betting site.",
  "tabs.overview": "Overview", "tabs.prediction": "AI Analysis", "tabs.stats": "Stats", "tabs.h2h": "H2H", "tabs.lineups": "Lineups",
  "tabs.standings": "Standings",
};
export type Lang = "fr" | "en";
const DICTS: Record<Lang, Dict> = { fr, en };
export type TKey = keyof Dict;

const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: (k: TKey) => string; locale: string }>({
  lang: "fr", setLang: () => {}, t: (k) => fr[k], locale: "fr-FR",
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("fr");
  // Interface en français uniquement (les textes d'analyse produits par le pipeline sont en français).
  useEffect(() => { try { localStorage.removeItem("lang"); } catch {} }, []);
  const setLang = (l: Lang) => { setLangState(l); try { localStorage.setItem("lang", l); } catch {} document.documentElement.lang = l; };
  return <Ctx.Provider value={{ lang, setLang, t: (k) => DICTS[lang][k], locale: lang === "fr" ? "fr-FR" : "en-GB" }}>{children}</Ctx.Provider>;
}
export const useI18n = () => useContext(Ctx);
