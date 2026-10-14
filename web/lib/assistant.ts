/* Assistant statistique (serveur). Moteur local : comprend des questions simples en français et répond uniquement à partir
   des données publiées (matchs, équipes, classements, performances). Il ne recommande jamais de pari.
   Le même moteur fournit le « contexte » transmis au modèle de langage quand ANTHROPIC_API_KEY est configurée. */
import "server-only";
import { getCompetitions, getMarkets, getMatches, getMeta, getPerformance, getStandings, getTeams } from "./data";
import type { Match, Team } from "./types";

export interface Reply { text: string; links: { label: string; href: string }[]; context: string }

const norm = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();
const P = (x: number | null | undefined, d = 0) => (x == null ? "—" : `${(100 * x).toFixed(d).replace(".", ",")} %`);
const N = (x: number | null | undefined, d = 1) => (x == null ? "—" : x.toFixed(d).replace(".", ","));

const STOP = new Set(["fc", "ac", "as", "sc", "afc", "cf", "de", "la", "le", "real", "united", "city", "club", "sv", "tsg", "1", "madrid", "manchester", "borussia", "athletic", "atletico", "hotspur", "albion", "town", "hove", "saint", "germain", "deportivo", "racing", "sporting", "olympique", "stade"]);
const ALIAS: Record<string, string> = { psg: "paris-saint-germain", barca: "barcelona", om: "marseille", ol: "lyon", man: "", city: "", inter: "inter", bayern: "bayern-munich", atletico: "atletico-madrid", juve: "juventus", spurs: "tottenham-hotspur", gladbach: "borussia-monchengladbach" };

function now(): number {
  const m = getMeta();
  return m.now ? new Date(m.now).getTime() : Date.now();
}

/** Équipes citées dans la question, dans l'ordre d'apparition. */
export function findTeams(q: string): Team[] {
  const t = ` ${norm(q)} `;
  const found: { team: Team; pos: number; len: number }[] = [];
  const covered = (pos: number) => found.some((f) => pos >= f.pos && pos < f.pos + f.len + 1);
  // 1) noms complets, noms courts et slugs : correspondances sûres
  for (const team of getTeams()) {
    for (const n of [team.name, team.short, team.slug.replace(/-/g, " ")].map(norm)) {
      const pos = t.indexOf(` ${n} `);
      if (n.length >= 3 && pos >= 0) { found.push({ team, pos, len: n.length }); break; }
    }
  }
  // 2) surnoms usuels
  for (const [a, slug] of Object.entries(ALIAS)) {
    const pos = t.indexOf(` ${a} `);
    const team = slug ? getTeams().find((x) => x.slug === slug) : undefined;
    if (pos >= 0 && team && !covered(pos) && !found.some((f) => f.team === team)) found.push({ team, pos, len: a.length });
  }
  // 3) un mot distinctif du nom (« Sociedad », « Forest »), seulement hors des noms déjà reconnus
  for (const team of getTeams()) {
    if (found.some((f) => f.team === team)) continue;
    for (const w of norm(team.name).split(" ").filter((w) => w.length >= 4 && !STOP.has(w))) {
      const pos = t.indexOf(` ${w} `);
      if (pos >= 0 && !covered(pos)) { found.push({ team, pos, len: w.length }); break; }
    }
  }
  found.sort((a, b) => a.pos - b.pos || b.len - a.len);
  const out: Team[] = [];
  for (const f of found) if (!out.includes(f.team) && !out.some((o) => found.find((g) => g.team === o)!.pos === f.pos)) out.push(f.team);
  return out;
}

const matchUrl = (m: Match) => `/match/${m.slug}`;
function nextMatch(slug: string): Match | undefined {
  const t = now();
  return getMatches().filter((m) => (m.home === slug || m.away === slug) && m.status === "scheduled" && new Date(m.kickoff).getTime() > t - 3 * 3600e3)[0];
}
function matchBetween(a: string, b: string): Match | undefined {
  const ms = getMatches().filter((m) => (m.home === a && m.away === b) || (m.home === b && m.away === a));
  return ms.find((m) => m.status === "scheduled") ?? ms[ms.length - 1];
}

function describeMatch(m: Match): string[] {
  const p = m.prediction;
  const out = [`**${m.homeName} – ${m.awayName}** (${new Date(m.kickoff).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })})`];
  if (m.status === "finished" && m.score) out.push(`Résultat : ${m.score.home}–${m.score.away}.`);
  if (!p) { out.push("Pas de prédiction disponible pour ce match."); return out; }
  out.push(`Probabilités du modèle : ${m.homeName} ${P(p.home)}, nul ${P(p.draw)}, ${m.awayName} ${P(p.away)}.`);
  out.push(`Buts attendus ${N(p.xg.home)} – ${N(p.xg.away)} · score le plus probable ${p.likelyScore.home}–${p.likelyScore.away} (${P(p.likelyScore.p)}) · plus de 2,5 buts ${P(p.over25)} · les deux marquent ${P(p.btts)}.`);
  if (p.expected?.corners) out.push(`Corners attendus ${N(p.expected.corners.mean)} (80 % des cas entre ${p.expected.corners.range[0]} et ${p.expected.corners.range[1]}), cartons jaunes ${N(p.expected.cards?.mean)}.`);
  if (p.context?.notes.length) out.push(`Contexte : ${p.context.notes.join(" ; ")}.`);
  if (p.similar) out.push(`Dans ${p.similar.n} matchs comparables : victoire à domicile ${P(p.similar.homeWin)}, nul ${P(p.similar.draw)}, victoire à l'extérieur ${P(p.similar.awayWin)}, ${N(p.similar.avgGoals, 2)} buts en moyenne.`);
  if (p.market) out.push(`Marché (cotes, marge retirée) : ${P(p.market.home)} / ${P(p.market.draw)} / ${P(p.market.away)} — ${p.market.agreement} avec le modèle.`);
  out.push(`Indice de confiance ${P(p.confidence)} : à ce niveau, l'issue la plus probable s'est réalisée environ ${P(p.confidence)} du temps. Ce n'est jamais une certitude.`);
  return out;
}

function describeTeam(t: Team): string[] {
  const s = t.stats;
  const out = [`**${t.name}** — ${t.rank ? `${t.rank}e, ${t.points} pts` : "classement indisponible"} · Elo ${t.elo ?? "—"}`];
  out.push(`Forme (5 derniers) : ${t.form.map((r) => (r === "W" ? "V" : r === "D" ? "N" : "D")).join(" ") || "—"} · ${N(s.ppg, 2)} pts/match sur ${s.window} matchs.`);
  out.push(`Buts marqués ${N(s.goalsFor, 2)} / encaissés ${N(s.goalsAgainst, 2)} par match · xG ${N(s.xgFor, 2)} pour, ${N(s.xgAgainst, 2)} contre.`);
  out.push(`Corners ${N(s.corners)} par match · cartons jaunes ${N(s.yellow, 2)} · clean sheets ${P(s.cleanSheetPct)} · matchs à +2,5 buts ${P(s.over25Pct)}.`);
  return out;
}

function compareTeams(a: Team, b: Team): string[] {
  const rows: [string, number | null, number | null, number][] = [
    ["Points / match", a.stats.ppg, b.stats.ppg, 2], ["Buts marqués / match", a.stats.goalsFor, b.stats.goalsFor, 2],
    ["Buts encaissés / match", a.stats.goalsAgainst, b.stats.goalsAgainst, 2], ["xG / match", a.stats.xgFor, b.stats.xgFor, 2],
    ["Corners / match", a.stats.corners, b.stats.corners, 1], ["Elo", a.elo, b.elo, 0],
  ];
  return [`**${a.name} vs ${b.name}** (10 derniers matchs)`, ...rows.map(([k, x, y, d]) => `- ${k} : ${N(x, d)} contre ${N(y, d)}`)];
}

const GLOSSAIRE: [RegExp, string][] = [
  [/\bxg\b|expected goals|buts attendus/, "Les **buts attendus (xG)** estiment combien de buts une équipe « aurait dû » marquer d'après ses tirs cadrés. Ici, c'est une approximation : tirs cadrés × taux de conversion de la ligue."],
  [/\belo\b/, "Le **classement Elo** mesure le niveau global d'une équipe : il monte après une victoire, d'autant plus que l'adversaire est fort. 100 points d'écart ≈ 64 % de chances de gagner hors avantage du terrain."],
  [/log loss|logloss/, "La **log loss** pénalise les prédictions confiantes qui se trompent. Plus elle est basse, mieux c'est ; 1,07 correspond à des prédictions sans information, les cotes des bookmakers font environ 0,97."],
  [/brier/, "Le **score de Brier** est l'écart quadratique moyen entre probabilités annoncées et résultats (0 = parfait). Il complète la log loss."],
  [/calibr/, "Un modèle **calibré** annonce 40 % pour des issues qui se réalisent 40 % du temps. La page Performance IA montre la courbe de calibration."],
  [/confiance|fiabilit/, "L'**indice de confiance** est la fréquence à laquelle l'issue la plus probable s'est réalisée, dans le passé, pour des matchs prédits avec le même niveau de certitude."],
];

function isAny(t: string, words: string[]) { return words.some((w) => t.includes(w)); }

export function answer(question: string): Reply {
  const q = norm(question);
  const links: Reply["links"] = [];
  const teams = findTeams(question);
  const ctx: string[] = [];

  // 1. Cotes, risque, « recommandations »
  if (isAny(q, ["cote", "pari", "parier", "recommand", "conseil", "risque", "sure", "prudent", "value", "safe", "fiable"]) && teams.length === 0) {
    const mk = getMarkets();
    const low = mk.rows.filter((r) => r.family !== "Double chance" && r.p < 0.95).slice(0, 5);
    const dis = getMatches().filter((m) => m.status === "scheduled" && m.prediction?.market && m.prediction.market.agreement !== "accord").slice(0, 3);
    const lines = ["Je classe les issues par **niveau de risque statistique** ; je ne donne pas de conseil de pari.",
      "Issues les plus probables selon le modèle parmi les prochains matchs :",
      ...low.map((r) => `- ${r.homeName} – ${r.awayName} : ${r.market} — ${P(r.p)} (palier ${r.tier.slice(4)}, cote juste ${N(r.fairOdds, 2)})`)];
    if (dis.length) lines.push("Désaccords entre le modèle et le marché à étudier :", ...dis.map((m) => `- ${m.homeName} – ${m.awayName} : ${m.prediction!.market!.agreement}`));
    const t = mk.tiers?.[0];
    lines.push(t ? `Sur ${t.decisions.toLocaleString("fr-FR")} décisions du palier « très faible risque » testées, le taux réalisé est ${P(t.observed, 1)} pour ${P(t.predicted, 1)} annoncé, mais le rendement aux cotes réelles est ${(t.returnAtOdds * 100).toFixed(1).replace(".", ",")} % : moins de risque ne veut pas dire meilleure affaire.` : "");
    links.push({ label: "Cotes & risque", href: "/markets" });
    return { text: lines.filter(Boolean).join("\n"), links, context: lines.join("\n") };
  }

  // 2. Deux équipes : match ou comparaison
  if (teams.length >= 2) {
    const [a, b] = teams;
    const m = matchBetween(a.slug, b.slug);
    const lines = m ? describeMatch(m) : compareTeams(a, b);
    if (m) links.push({ label: `${m.homeName} – ${m.awayName}`, href: matchUrl(m) });
    else lines.push("Aucun match entre ces deux équipes n'est programmé dans les données publiées.");
    links.push({ label: a.name, href: `/team/${a.slug}` }, { label: b.name, href: `/team/${b.slug}` });
    ctx.push(...lines, ...describeTeam(a), ...describeTeam(b));
    return { text: lines.join("\n"), links, context: ctx.join("\n") };
  }

  // 3. Une équipe
  if (teams.length === 1) {
    const t = teams[0];
    const lines = describeTeam(t);
    const m = nextMatch(t.slug);
    if (m) { lines.push("", "Prochain match :", ...describeMatch(m)); links.push({ label: `${m.homeName} – ${m.awayName}`, href: matchUrl(m) }); }
    links.push({ label: t.name, href: `/team/${t.slug}` });
    return { text: lines.join("\n"), links, context: lines.join("\n") };
  }

  // 4. Compétition
  const COMP_ALIAS: Record<string, string[]> = { "premier-league": ["premier league", "angleterre", "anglais"], laliga: ["laliga", "la liga", "liga", "espagne", "espagnol"],
    "serie-a": ["serie a", "italie", "calcio"], bundesliga: ["bundesliga", "allemagne"], "ligue-1": ["ligue 1", "france", "l1"] };
  const has = (w: string) => ` ${q} `.includes(` ${w} `);
  const comp = getCompetitions().find((c) => has(norm(c.name)) || (COMP_ALIAS[c.slug] ?? []).some(has));
  if (comp && comp.covered) {
    const st = getStandings(comp.slug).slice(0, 5);
    const names = Object.fromEntries(getTeams().map((x) => [x.slug, x.name]));
    const lines = [`**${comp.name}** — saison ${comp.season ?? ""}`, ...st.map((r) => `${r.rank}. ${names[r.team] ?? r.team} — ${r.points} pts (${r.played} matchs, ${r.gd > 0 ? "+" : ""}${r.gd})`)];
    if (comp.stats) lines.push(`${N(comp.stats.goalsPerMatch, 2)} buts par match · victoire à domicile ${P(comp.stats.homeWinPct)} · +2,5 buts ${P(comp.stats.over25Pct)}.`);
    links.push({ label: comp.name, href: `/competition/${comp.slug}` });
    return { text: lines.join("\n"), links, context: lines.join("\n") };
  }

  // 5. Performance du modèle
  if (isAny(q, ["performance", "precision", "precis", "fiable le modele", "modele", "taux de reussite", "accuracy"])) {
    const p = getPerformance();
    const lines = [`Le modèle a été évalué sur **${p.matches.toLocaleString("fr-FR")} matchs** qu'il n'avait jamais vus.`,
      `Bonne issue prédite ${P(p.accuracy, 1)} (cotes ${P(p.market.accuracy, 1)}) · log loss ${N(p.logLoss, 3)} (cotes ${N(p.market.logLoss, 3)}, sans information ${N(p.baseline.logLoss, 3)}) · Brier ${N(p.brier, 3)} · calibration (ECE) ${N(p.ece, 3)}.`,
      "Il est bien calibré mais reste un peu moins précis que les cotes des bookmakers, qui intègrent compositions et blessures."];
    links.push({ label: "Performance IA", href: "/ai-performance" });
    return { text: lines.join("\n"), links, context: lines.join("\n") };
  }

  // 6. Glossaire
  for (const [re, txt] of GLOSSAIRE) if (re.test(q)) return { text: txt, links: [{ label: "Performance IA", href: "/ai-performance" }], context: txt };

  // 7. Programme
  if (isAny(q, ["aujourd", "ce soir", "demain", "week end", "weekend", "prochain", "programme", "calendrier", "matchs"])) {
    const t0 = now();
    const day = isAny(q, ["demain"]) ? 1 : 0;
    const start = new Date(t0); start.setUTCHours(0, 0, 0, 0); start.setUTCDate(start.getUTCDate() + day);
    const end = new Date(start); end.setUTCDate(end.getUTCDate() + (isAny(q, ["week end", "weekend", "prochain", "programme", "calendrier"]) ? 4 : 1));
    const ms = getMatches().filter((m) => { const k = new Date(m.kickoff).getTime(); return k >= start.getTime() && k < end.getTime(); }).slice(0, 10);
    const lines = ms.length ? [`${ms.length} match(s) :`, ...ms.map((m) => `- ${m.homeName} – ${m.awayName}${m.prediction ? ` : ${P(m.prediction.home)} / ${P(m.prediction.draw)} / ${P(m.prediction.away)}` : ""}${m.score && m.status === "finished" ? ` (${m.score.home}–${m.score.away})` : ""}`)]
      : ["Aucun match publié sur cette période."];
    links.push({ label: "Match Center", href: "/" });
    return { text: lines.join("\n"), links, context: lines.join("\n") };
  }

  // 8. Aide
  const text = ["Je réponds à partir des données statistiques du site. Exemples :",
    "- « Analyse Arsenal – Chelsea »", "- « Forme de Barcelona »", "- « Classement de la Serie A »",
    "- « Quels sont les matchs les moins risqués ? »", "- « Le modèle est-il fiable ? »", "- « C'est quoi les xG ? »"].join("\n");
  return { text, links: [], context: "" };
}

/** Contexte compact transmis au modèle de langage (en plus de la réponse du moteur local). */
export function globalContext(): string {
  const m = getMeta();
  const p = getPerformance();
  return `Données au ${m.dataAsOf}, mode ${m.mode}, modèle ${m.model}. Performance hors échantillon : ${p.matches} matchs, accuracy ${P(p.accuracy, 1)}, log loss ${p.logLoss.toFixed(3)} (cotes ${p.market.logLoss.toFixed(3)}).`;
}
