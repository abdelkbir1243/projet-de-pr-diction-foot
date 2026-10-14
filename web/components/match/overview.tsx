"use client";
/* OVERVIEW : synthèse IA, Form Guide des deux équipes, comparaison rapide, déroulé. */
import Link from "next/link";
import { ArrowRight, BrainCircuit, Info } from "lucide-react";
import type { LiveState, Match, Team, TeamLite } from "@/lib/types";
import { useI18n } from "@/lib/i18n";
import { cn, num, pct } from "@/lib/utils";
import { AIBadge, FormGuide, ProbabilityBar, TeamLink, TeamLogo } from "../football";
import { Card, CardHeader, EmptyState } from "../ui/primitives";
import { MatchStatsCard } from "./timeline";
import { ContextCard, ExpectedStatsCard, PredictionSource } from "./analysis-cards";
import { TrustCard } from "../confidence";
import { TeamComparison } from "./team-comparison";

export function FormGuideCard({ team, venue, teams }: { team: Team; venue: "home" | "away"; teams: Record<string, TeamLite> }) {
  const { locale } = useI18n();
  const last = team.lastMatches.slice(0, 5);
  const vb = venue === "home" ? team.stats.home : team.stats.away;
  return (
    <Card>
      <CardHeader title={`Form Guide · ${team.name}`} icon={<TeamLogo team={teams[team.slug] ?? team} size={20} />}
        action={<span className="text-[11px] text-text-3">{team.rank ? `${team.rank}e · ` : ""}Elo {team.elo ?? "—"}</span>} />
      <div className="px-4">
        <FormGuide size="md" items={[...last].reverse().map((r) => ({ result: r.result, title: `${r.opponentName} ${r.gf}–${r.ga}` }))} />
        <div className="tabular mt-3 grid grid-cols-3 gap-2 text-center">
          {[["Buts marqués", num(team.stats.goalsFor, 2)], ["Buts encaissés", num(team.stats.goalsAgainst, 2)], [venue === "home" ? "Pts/m à dom." : "Pts/m à l'ext.", num(vb?.ppg, 2)]].map(([k, v]) => (
            <div key={k} className="rounded-lg bg-surface-2 py-2"><div className="truncate text-[10px] uppercase tracking-wide text-text-3">{k}</div><div className="text-[15px] font-semibold">{v}</div></div>
          ))}
        </div>
      </div>
      <ul className="mt-3 divide-y divide-border border-t border-border">
        {last.map((r, i) => (
          <li key={i} className="grid grid-cols-[22px_52px_1fr_auto] items-center gap-2 px-4 py-2 text-[13px]">
            <FormGuide items={[r.result]} />
            <span className="text-xs text-text-3">{new Date(r.date).toLocaleDateString(locale, { day: "2-digit", month: "short" })}</span>
            <span className="flex min-w-0 items-center gap-1.5"><span className="text-[10px] uppercase text-text-3">{r.venue === "home" ? "dom" : "ext"}</span>
              <TeamLink team={teams[r.opponent]} slug={r.opponent} className="truncate">{r.opponentName}</TeamLink></span>
            <span className="tabular font-semibold">{r.gf}–{r.ga}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function Overview({ m, home, away, teams, state, covered }: { m: Match; home: Team | null; away: Team | null; teams: Record<string, TeamLite>; state: LiveState; covered: boolean }) {
  const { t } = useI18n();
  const p = m.prediction;
  return (
    <div className="space-y-4">
      {p ? (
        <Card className="relative overflow-hidden">
          <span className="ai-gradient absolute inset-x-0 top-0 h-0.5" aria-hidden />
          <CardHeader title={<span className="inline-flex items-center gap-2"><AIBadge label="AI Prediction" /></span>} subtitle="Probabilités statistiques, jamais des résultats garantis"
            action={<span className="flex items-center gap-2"><PredictionSource p={p} /><Link href="?tab=prediction" scroll={false} className="hidden items-center gap-1 text-xs font-semibold text-brand hover:underline sm:inline-flex">AI Analysis<ArrowRight className="size-3.5" /></Link></span>} />
          <div className="grid gap-5 px-4 pb-4 md:grid-cols-[1fr_auto] md:items-center">
            <ProbabilityBar home={p.home} draw={p.draw} away={p.away} labels={[m.homeName, t("match.draw"), m.awayName]} />
            <dl className="tabular grid grid-cols-4 gap-3 text-center md:w-[340px]">
              {[["Confiance", pct(p.confidence)], ["Score", `${p.likelyScore.home}–${p.likelyScore.away}`], ["xG", p.xg.total.toFixed(1)], ["+2,5", pct(p.over25)]].map(([k, v]) => (
                <div key={k}><dt className="text-[10px] uppercase tracking-wide text-text-3">{k}</dt><dd className="text-[17px] font-semibold">{v}</dd></div>
              ))}
            </dl>
          </div>
        </Card>
      ) : (
        <Card><EmptyState icon={<Info className="size-5" />} title={t("match.noPrediction")}
          hint={m.status === "cancelled" ? "Match annulé." : covered ? "Aucune prédiction n'a été enregistrée avant le coup d'envoi : nous n'en publions jamais après coup." : "Cette compétition n'est pas couverte par le modèle."} /></Card>
      )}
      {p?.trust && <TrustCard trust={p.trust} />}
      {state.status === "finished" && <MatchStatsCard m={m} />}
      {p?.context && <ContextCard ctx={p.context} homeName={m.homeName} awayName={m.awayName} />}
      {p?.expected && state.status !== "finished" && <ExpectedStatsCard p={p} />}
      <div className="grid gap-4 lg:grid-cols-2">
        {home && <FormGuideCard team={home} venue="home" teams={teams} />}
        {away && <FormGuideCard team={away} venue="away" teams={teams} />}
      </div>
      {home && away && <TeamComparison home={home} away={away} title="Comparaison rapide" limit={6} />}
      {!home && !away && <Card><EmptyState icon={<BrainCircuit className="size-5" />} title="Données d'équipes indisponibles" /></Card>}
      
    </div>
  );
}
