/* Indicateurs dérivés pour l'analyse d'un match (fonctions pures, sans dépendance UI).
   Les « ratings » sont des percentiles 0-100 au sein du championnat, calculés par le pipeline (team.radar). */
import type { Prediction, Team } from "./types";

/** Régularité : 100 = résultats très constants sur les 10 derniers matchs (écart-type des points faible). */
export function consistency(t: Team): number {
  const pts: number[] = t.lastMatches.map((m) => (m.result === "W" ? 3 : m.result === "D" ? 1 : 0));
  if (pts.length < 3) return 50;
  const mean = pts.reduce((a, b) => a + b, 0) / pts.length;
  const sd = Math.sqrt(pts.reduce((a, b) => a + (b - mean) ** 2, 0) / pts.length);
  return Math.round(Math.max(0, Math.min(100, 100 * (1 - sd / 1.5))));
}

export interface Rating { key: string; label: string; home: number; away: number; hint: string }

export function ratings(home: Team, away: Team): Rating[] {
  return [
    { key: "form", label: "Form Rating", home: home.radar.form, away: away.radar.form, hint: "Points sur les 5 derniers matchs" },
    { key: "attack", label: "Attack Rating", home: home.radar.attack, away: away.radar.attack, hint: "xG produits (10 derniers matchs)" },
    { key: "defense", label: "Defense Rating", home: home.radar.defense, away: away.radar.defense, hint: "xG concédés (10 derniers matchs)" },
    { key: "venue", label: "Home / Away", home: home.radar.venueHome, away: away.radar.venueAway, hint: "Domicile pour l'un, extérieur pour l'autre" },
  ];
}

export function radarAxes(home: Team, away: Team) {
  return [
    { axis: "Attack", home: home.radar.attack, away: away.radar.attack },
    { axis: "Defense", home: home.radar.defense, away: away.radar.defense },
    { axis: "Form", home: home.radar.form, away: away.radar.form },
    { axis: "Possession", home: home.radar.control, away: away.radar.control },
    { axis: "Finishing", home: home.radar.finishing, away: away.radar.finishing },
    { axis: "Consistency", home: consistency(home), away: consistency(away) },
  ];
}

export interface Factor { label: string; detail: string; side: "home" | "away" | "neutral"; weight: number }

/** Facteurs qui expliquent les probabilités : écarts les plus marqués entre les deux équipes, classés par importance. */
export function keyFactors(home: Team, away: Team, p: Prediction): Factor[] {
  const f: Factor[] = [];
  const add = (label: string, diff: number, scale: number, fmt: (side: "home" | "away") => string) => {
    const w = Math.min(1, Math.abs(diff) / scale);
    if (w < 0.15) return;
    const side = diff > 0 ? "home" : "away";
    f.push({ label, detail: fmt(side), side, weight: w });
  };
  const nm = (s: "home" | "away") => (s === "home" ? home.name : away.name);
  add("Niveau global (Elo)", (home.elo ?? 1500) - (away.elo ?? 1500), 200, (s) => `${nm(s)} +${Math.abs(Math.round((home.elo ?? 0) - (away.elo ?? 0)))} points Elo`);
  add("Forme récente", (home.stats.ppg ?? 0) - (away.stats.ppg ?? 0), 1.2, (s) => `${nm(s)} : ${(s === "home" ? home : away).stats.ppg?.toFixed(2)} pts/match`);
  add("Production offensive", (home.stats.xgFor ?? 0) - (away.stats.xgFor ?? 0), 0.8, (s) => `${nm(s)} : ${(s === "home" ? home : away).stats.xgFor?.toFixed(2)} xG/match`);
  add("Solidité défensive", (away.stats.xgAgainst ?? 0) - (home.stats.xgAgainst ?? 0), 0.8, (s) => `${nm(s)} : ${(s === "home" ? home : away).stats.xgAgainst?.toFixed(2)} xG concédés`);
  add("Domicile / extérieur", (home.stats.home?.ppg ?? 1.5) - (away.stats.away?.ppg ?? 1.2), 1.2,
    (s) => (s === "home" ? `${home.name} : ${home.stats.home?.ppg?.toFixed(2)} pts/match à domicile` : `${away.name} : ${away.stats.away?.ppg?.toFixed(2)} pts/match à l'extérieur`));
  f.sort((a, b) => b.weight - a.weight);
  if (p.draw >= 0.28) f.push({ label: "Match serré", detail: `Probabilité de nul élevée (${Math.round(p.draw * 100)} %)`, side: "neutral", weight: p.draw });
  return f.slice(0, 5);
}

export function uncertaintyLabel(p: Prediction) {
  const m = Math.max(p.home, p.draw, p.away);
  return m < 0.45 ? { label: "Incertitude élevée", tone: "warn" as const } : m < 0.6 ? { label: "Incertitude significative", tone: "neutral" as const } : { label: "Favori net", tone: "brand" as const };
}
