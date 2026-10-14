/* Couche d'accès aux données (serveur). Aujourd'hui : fichiers JSON produits par le pipeline Python.
   Pour brancher une API FastAPI, il suffit de réimplémenter ces fonctions (mêmes types de retour). */
import "server-only";
import metaJson from "@/data/meta.json";
import competitionsJson from "@/data/competitions.json";
import teamsJson from "@/data/teams.json";
import standingsJson from "@/data/standings.json";
import matchesJson from "@/data/matches.json";
import performanceJson from "@/data/performance.json";
import teamIndexJson from "@/data/team-index.json";
import marketsJson from "@/data/markets.json";
import daysJson from "@/data/days.json";
import type { Competition, DaySummary, MarketsFile, Match, MatchSummary, Meta, Performance, StandingRow, Team, TeamLite } from "./types";

const meta = metaJson as Meta;
const competitions = competitionsJson as unknown as Competition[];
const teams = teamsJson as unknown as Team[];
const standings = standingsJson as unknown as Record<string, StandingRow[]>;
const matches = (matchesJson as unknown as Match[]).slice().sort((a, b) => a.kickoff.localeCompare(b.kickoff));
const performance = performanceJson as unknown as Performance;
const teamMap = new Map(teams.map((t) => [t.slug, t]));

export const COMPETITION_ORDER = ["champions-league", "europa-league", "conference-league", "premier-league", "laliga", "serie-a", "bundesliga", "ligue-1"];
export const isPredicted = (c: { covered: boolean; model?: string | null }) => c.covered || c.model === "cup";

export const getMeta = () => meta;
export const getCompetitions = () => [...competitions].sort((a, b) => COMPETITION_ORDER.indexOf(a.slug) - COMPETITION_ORDER.indexOf(b.slug));
export const getCompetition = (slug: string) => competitions.find((c) => c.slug === slug) ?? null;
export const getTeams = () => teams;
export const getTeam = (slug: string | null | undefined) => (slug ? teamMap.get(slug) ?? null : null);
export const getStandings = (competition: string) => standings[competition] ?? [];
export const getMatches = () => matches;
export const getMatch = (slug: string) => matches.find((m) => m.slug === slug) ?? null;
export const getPerformance = () => performance;
const markets = marketsJson as unknown as MarketsFile;
export const getMarkets = () => markets;
const days = daysJson as unknown as Record<string, DaySummary>;
export const getDays = () => days;
export const getTeamMatches = (team: string) => matches.filter((m) => m.home === team || m.away === team);
export const getCompetitionMatches = (competition: string) => matches.filter((m) => m.competition === competition);

export function summarize(m: Match): MatchSummary {
  const { h2h: _h, prediction, ...rest } = m;
  return {
    ...rest,
    prediction: prediction
      ? { home: prediction.home, draw: prediction.draw, away: prediction.away, confidence: prediction.confidence, xg: prediction.xg,
          likelyScore: prediction.likelyScore, over25: prediction.over25, btts: prediction.btts, level: prediction.trust?.level }
      : null,
  };
}

/** Petites fiches d'équipes pour les composants clients (logos, noms). */
export function teamLite(slugs?: Iterable<string | null>): Record<string, TeamLite> {
  const index = teamIndexJson as Record<string, { name: string; short: string; code: string; color: string }>;
  if (!slugs) return Object.fromEntries(teams.map((t) => [t.slug, { slug: t.slug, name: t.name, short: t.short, code: t.code, color: t.color, competition: t.competition }]));
  const out: Record<string, TeamLite> = {};
  for (const s of new Set(slugs)) {
    if (!s) continue;
    const t = teamMap.get(s);
    if (t) out[s] = { slug: t.slug, name: t.name, short: t.short, code: t.code, color: t.color, competition: t.competition };
    else if (index[s]) out[s] = { slug: s, ...index[s], competition: "" };      // équipe sans page (reléguée) : logo et nom seulement
  }
  return out;
}
