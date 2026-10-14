/* Types partagés — identiques au format produit par le pipeline Python (footpred/web.py) et, demain, par une API FastAPI. */

export type Result = "W" | "D" | "L";
export type MatchStatus = "scheduled" | "live" | "halftime" | "finished" | "postponed" | "cancelled";

/** live : scores en direct (football-data.org) · fixtures : calendrier + cotes (football-data.co.uk) ·
 *  offline : aucune source joignable, derniers résultats connus · replay : date passée rejouée (tests, démonstration). */
export type DataMode = "live" | "fixtures" | "offline" | "replay";

export interface Meta {
  generatedAt: string;
  dataAsOf: string;
  resultsAddedFromApi: number;
  mode: DataMode;
  referenceDate: string;
  /** Horloge figée (mode rejeu uniquement). */
  now: string | null;
  model: string;
  sources: string[];
  liveScores: boolean;
  /** Fraîcheur des résultats : dernier résultat connu, matchs joués sans score publié, retard en jours. */
  freshness?: { lastResult: string; missingResults: number; lagDays: number; stale: boolean; journalRemoved?: number };
}

export interface Competition {
  slug: string;
  code: string;
  name: string;
  country: string;
  cc: string;
  covered: boolean;
  /** league : modèle complet des championnats · cup : modèle Elo des coupes d'Europe · null : pas de prédiction. */
  model?: "league" | "cup" | null;
  zones: { cl?: [number, number]; el?: [number, number]; rel?: [number, number] };
  season: string | null;
  teams: string[];
  nTeams: number;
  stats: null | {
    matches: number; goalsPerMatch: number; homeWinPct: number; drawPct: number; awayWinPct: number;
    over25Pct: number; bttsPct: number; cornersPerMatch: number | null; yellowPerMatch: number | null;
  };
}

export interface VenueBlock { played: number; ppg: number | null; gf: number | null; ga: number | null; winPct: number | null }

export interface Team {
  slug: string;
  name: string;
  short: string;
  code: string;
  color: string;
  competition: string;
  country: string;
  stadium: string | null;
  coach: string | null;
  elo: number | null;
  rank?: number;
  points?: number;
  form: Result[];
  lastMatches: { date: string; opponent: string; opponentName: string; venue: "home" | "away"; gf: number; ga: number; result: Result; competition: string | null }[];
  stats: {
    window: number; ppg: number | null; goalsFor: number | null; goalsAgainst: number | null; xgFor: number | null; xgAgainst: number | null;
    shots: number | null; shotsAgainst: number | null; shotsOnTarget: number | null; corners: number | null; cornersAgainst: number | null;
    yellow: number | null; red: number | null; fouls: number | null; shotShare: number | null; cleanSheetPct: number | null;
    over25Pct: number | null; bttsPct: number | null; home: VenueBlock | null; away: VenueBlock | null;
    season: Partial<VenueBlock> & { label: string; played: number };
  };
  eloHistory: { date: string; elo: number }[];
  radar: { attack: number; defense: number; form: number; control: number; finishing: number; venueHome: number; venueAway: number };
}

export interface StandingRow {
  rank: number; team: string; played: number; won: number; drawn: number; lost: number; gf: number; ga: number; gd: number; points: number; form: Result[];
}

/** Calibration historique : quand le modèle annonçait une probabilité de cette classe, fréquence observée (IC 95 % de Wilson). */
export interface Calib { n: number; announced: number; observed: number; lo: number; hi: number }
export interface Market { family: string; market: string; p: number; tier: string; cal?: Calib | null }

export type TrustLevel = "A" | "B" | "C";
export interface Trust {
  level: TrustLevel; label: string; favorite: string; p: number;
  evidence: (Calib & { level: TrustLevel; from: number; to: number }) | null;
  factors: { label: string; effect: "plus" | "minus" | "neutral"; detail: string }[];
}

export interface Range { expected: number; range: [number, number] }
export interface DaySummary {
  date: string; n: number; levels: Record<TrustLevel, number>;
  goals: Range & { perMatch: number }; corners: Range | null;
  homeWins: Range; draws: Range; awayWins: Range; favWins: Range; over25: Range;
  clearest: { match: string; label: string; p: number }; mostOpen: { match: string; label: string; p: number };
  best: { match: string; homeName: string; awayName: string; market: string; family: string; p: number; observed: number; lo: number; hi: number; n: number }[];
  result: null | { n: number; goals: number; goalsExpected: number; homeWins: number; draws: number; awayWins: number; favWins: number; favExpected: number;
    over25: number; over25Expected: number; logLoss: number };
}

export interface Prediction {
  model: string;
  home: number; draw: number; away: number;
  confidence: number;
  reliability: "faible" | "moyenne" | "bonne" | "élevée";
  endOfSeason: boolean;
  xg: { home: number; away: number; total: number };
  likelyScore: { home: number; away: number; p: number };
  topScores: { score: string; p: number }[];
  over15: number; over25: number; over35: number; btts: number;
  cleanSheetHome: number; cleanSheetAway: number; firstHalfGoal: number;
  control: number | null;
  corners: { total: number; home: number; away: number; over: Record<string, number> } | null;
  cards: { total: number; home: number; away: number; over: Record<string, number>; red: number } | null;
  /** cup : modèle simplifié des coupes d'Europe (Elo uniquement). */
  scope?: "cup";
  elo?: { home: number; away: number; homeEstimated: boolean; awayEstimated: boolean };
  markets: Market[];
  decisions: { profile: string; market: string; p: number; tier: string }[];
  synthesis: string;
  frozenAt?: string;
  /** Degré de confiance mesuré hors échantillon (A élevé, B moyen, C faible). */
  trust?: Trust | null;
  /** pre-match : calculée avant le match · frozen : figée avant le coup d'envoi (journal) ·
   *  out-of-sample : match déjà joué, prédit par un modèle entraîné sur les saisons précédentes. */
  source?: "pre-match" | "frozen" | "out-of-sample";
  expected?: Expected;
  similar?: Similar | null;
  context?: MatchContext | null;
  market?: MarketComparison | null;
}

export interface RangeStat { mean: number; range: [number, number]; home: number; away: number }
export interface Expected { goals: RangeStat & { dist: number[] }; corners?: RangeStat; cards?: RangeStat }

export interface Similar {
  n: number; homeWin: number; draw: number; awayWin: number; avgGoals: number; over25: number; btts: number;
  corners: number; cards: number; eloGap: [number, number];
}

export interface TeamContext {
  rest: number | null; load21: number | null; played: number | null; rank: number | null;
  promoted: boolean; firstSeason: boolean; champion: boolean;
  titleRace: boolean; europeRace: boolean; relegationFight: boolean; nothingToPlayFor: boolean;
}
export interface MatchContext { home: TeamContext; away: TeamContext; notes: string[]; seasonStart: boolean }

export interface Odds { home?: number; draw?: number; away?: number; over25?: number; under25?: number }
export interface MarketComparison {
  odds: Odds; margin: number; home: number; draw: number; away: number; over25?: number;
  rows: { key: keyof Odds; label: string; model: number; market: number; gap: number; fairOdds: number; odds: number | null }[];
  agreement: "accord" | "désaccord modéré" | "désaccord marqué";
  note: string;
}

export type SideStat = { home: number | null; away: number | null };
export interface MatchStats { shots: SideStat; shotsOnTarget: SideStat; corners: SideStat; yellow: SideStat; red: SideStat; fouls: SideStat }

export interface H2H {
  matches: { date: string; home: string; away: string; homeGoals: number; awayGoals: number; competition: string | null }[];
  summary: null | {
    n: number; homeWins: number; draws: number; awayWins: number; avgGoals: number; bttsPct: number; over25Pct: number;
    cleanSheetsHome: number; cleanSheetsAway: number;
  };
}

export interface Match {
  id: string;
  slug: string;
  competition: string;
  kickoff: string;
  status: MatchStatus;
  minute: number | null;
  venue: string | null;
  home: string | null;
  away: string | null;
  homeName: string;
  awayName: string;
  score: { home: number; away: number } | null;
  halftime: { home: number; away: number } | null;
  /** false : heure exacte inconnue (match issu de l'historique). */
  timeKnown: boolean;
  /** Statistiques réelles du match terminé (tirs, corners, cartons…). */
  stats: MatchStats | null;
  odds: Odds | null;
  /** Phase de la compétition (coupes d'Europe) et prolongation. */
  round?: string | null;
  extraTime?: boolean;
  prediction: Prediction | null;
  h2h: H2H;
  /** Coup d'envoi passé sans score connu ; au-delà de 2 h 15, en attente du résultat (aucune nouvelle prédiction publiée). */
  started?: boolean;
  awaitingResult?: boolean;
  /** État publié : scheduled | prematch_open | live | awaiting_result | finished | postponed | cancelled. */
  state?: "scheduled" | "prematch_open" | "live" | "awaiting_result" | "finished" | "postponed" | "cancelled";
}

/** Version allégée envoyée aux composants clients des listes. */
export type MatchSummary = Omit<Match, "h2h" | "prediction"> & {
  prediction: (Pick<Prediction, "home" | "draw" | "away" | "confidence" | "xg" | "likelyScore" | "over25" | "btts"> & { level?: TrustLevel }) | null;
};

export interface LiveState {
  status: MatchStatus; minute: number | null; score: { home: number; away: number } | null;
  /** Coup d'envoi passé mais aucun score en direct disponible : résultat publié à la prochaine mise à jour. */
  awaiting?: boolean;
}

export interface MarketRow {
  match: string; kickoff: string; competition: string; home: string; away: string; homeName: string; awayName: string;
  family: string; market: string; p: number; tier: string; fairOdds: number; odds: number | null; marketP: number | null;
}
export interface MarketsFile { rows: MarketRow[]; tiers: Performance["tiers"] }

export interface Performance {
  scope: string;
  matches: number; accuracy: number; logLoss: number; brier: number; rps: number; ece: number;
  baseline: { logLoss: number; accuracy: number };
  market: { logLoss: number; accuracy: number; brier: number };
  calibration: { predicted: number; observed: number; n: number }[];
  byMonth: { month: string; logLoss: number; marketLogLoss: number; accuracy: number; brier: number; n: number }[];
  tiers: { tier: string; decisions: number; predicted: number; observed: number; returnAtOdds: number }[] | null;
  live: null | { n: number; accuracy: number; logLoss: number; brier: number };
  confidence?: {
    levels: Record<TrustLevel, { label: string; n: number; announced: number; observed: number; lo: number; hi: number; logLoss: number; share: number }>;
    cells: (Calib & { level: TrustLevel; from: number; to: number })[];
  };
  families?: { family: string; n: number; ece: number; points: { announced: number; observed: number; n: number }[] }[];
  byDay?: { date: string; n: number; goalsExpected: number; goals: number; favExpected: number; favWins: number; homeExpected: number; homeWins: number;
    drawExpected: number; draws: number; over25Expected: number; over25: number; logLoss: number }[];
  backtest?: { matches: number; markets: number; seasons: [number, number]; lastDate: string | null };
  cups?: {
    matches: number; logLoss: number; baseline: number; accuracy: number; brier: number; ece: number;
    byCup: Record<string, { n: number; logLoss: number; accuracy: number }>;
    levels: Record<string, { label: string; n: number; announced: number; observed: number; lo: number; hi: number; logLoss: number; share: number }>;
  };
  history: {
    date: string; competition: string; home: string; away: string; homeName: string; awayName: string;
    pH: number; pD: number; pA: number; predicted: "H" | "D" | "A"; actual: "H" | "D" | "A"; score: string; correct: boolean;
  }[];
}

export interface TeamLite { slug: string; name: string; short: string; code: string; color: string; competition: string }
