import type { LiveState, MatchSummary } from "./types";

/** État d'un match à l'instant `now`. Aucune simulation : le statut et le score viennent des données publiées,
 *  remplacés par le flux en direct (/api/live) quand une clé football-data.org est configurée. */
export function liveState(m: MatchSummary, now: number, override?: LiveState): LiveState {
  if (override) return override;
  const base: LiveState = { status: m.status, minute: m.minute, score: m.score };
  if (m.status === "scheduled" && (m.awaitingResult || m.started || now > new Date(m.kickoff).getTime())) return { ...base, awaiting: true };
  return base;
}

export const isLive = (s: LiveState["status"]) => s === "live" || s === "halftime";

/** Une prédiction d'avant-match n'est consultable comme « à venir » que si le coup d'envoi est dans le futur et l'horaire fiable. */
export const isPrematchOpen = (m: MatchSummary, now: number) =>
  m.status === "scheduled" && !m.awaitingResult && !m.started && m.timeKnown !== false && new Date(m.kickoff).getTime() > now;
