"use client";
import Link from "next/link";
import { ArrowUpRight, BrainCircuit, Gauge, Scale, Sparkles } from "lucide-react";
import { useAssistant } from "./assistant";
import type { MatchSummary, Performance, TeamLite } from "@/lib/types";
import { useI18n } from "@/lib/i18n";
import { cn, pct } from "@/lib/utils";
import { ProbabilityBar, TeamLogo } from "./football";
import { Card, CardHeader } from "./ui/primitives";

/** PredictionCard : la prédiction IA d'un match, en un coup d'œil (probabilités, confiance, xG, score prédit, +2,5, BTTS). */
export function PredictionCard({ m, teams, className }: { m: MatchSummary; teams: Record<string, TeamLite>; className?: string }) {
  const { t, locale } = useI18n();
  const p = m.prediction;
  if (!p) return null;
  const h = m.home ? teams[m.home] : null, a = m.away ? teams[m.away] : null;
  const metrics: [string, string, number | null][] = [
    ["Confiance", pct(p.confidence), p.confidence],
    ["xG", p.xg.total.toFixed(1), null],
    ["Score", `${p.likelyScore.home}–${p.likelyScore.away}`, null],
    ["+2,5", pct(p.over25), p.over25],
    ["BTTS", pct(p.btts), p.btts],
  ];
  return (
    <Link href={`/match/${m.slug}?tab=prediction`} className={cn("card-hover group relative block overflow-hidden rounded-xl border border-border bg-surface p-4 shadow-card", className)}>
      <span className="ai-gradient absolute inset-x-0 top-0 h-0.5 opacity-80" aria-hidden />
      <div className="flex items-center justify-between text-[11px]">
        <span className="inline-flex items-center gap-1 font-bold uppercase tracking-[0.12em] text-brand"><Sparkles className="size-3.5" />AI Prediction</span>
        <span className="tabular text-text-3" suppressHydrationWarning>{new Date(m.kickoff).toLocaleString(locale, { weekday: "short", hour: "2-digit", minute: "2-digit" })}</span>
      </div>
      <div className="mt-3 grid grid-cols-[1fr_auto_1fr] items-center gap-2">
        <div className="flex min-w-0 items-center gap-2"><TeamLogo team={h} size={30} /><span className="truncate text-[13px] font-semibold">{m.homeName}</span></div>
        <span className="text-[11px] font-medium uppercase text-text-3">vs</span>
        <div className="flex min-w-0 flex-row-reverse items-center gap-2 text-right"><TeamLogo team={a} size={30} /><span className="truncate text-[13px] font-semibold">{m.awayName}</span></div>
      </div>
      <div className="mt-4"><ProbabilityBar home={p.home} draw={p.draw} away={p.away} labels={[h?.code ?? "1", t("match.draw"), a?.code ?? "2"]} /></div>
      <dl className="snap-row mt-4 border-t border-border pt-3">
        {metrics.map(([k, v]) => (
          <div key={k} className="min-w-[52px] flex-1">
            <dt className="truncate text-[10px] font-medium uppercase tracking-wide text-text-3">{k}</dt>
            <dd className="tabular text-[14px] font-semibold">{v}</dd>
          </div>
        ))}
      </dl>
    </Link>
  );
}
/** Compatibilité : ancien nom. */
export const ProbabilityCard = PredictionCard;

export function AIPerformanceMini({ perf }: { perf: Pick<Performance, "matches" | "accuracy" | "logLoss" | "market" | "baseline" | "ece"> }) {
  const skill = 1 - perf.logLoss / perf.baseline.logLoss, mskill = 1 - perf.market.logLoss / perf.baseline.logLoss;
  return (
    <Card>
      <CardHeader title="AI Performance" subtitle={`${perf.matches.toLocaleString("fr-FR")} matchs hors échantillon`} icon={<Gauge className="size-4 text-brand" />}
        action={<Link href="/ai-performance" className="inline-flex items-center gap-0.5 text-xs font-medium text-brand hover:underline">Détails<ArrowUpRight className="size-3.5" /></Link>} />
      <div className="space-y-3 px-4 pb-4">
        <div className="tabular grid grid-cols-2 gap-2">
          <div className="rounded-lg bg-surface-2 px-3 py-2"><div className="text-[10px] uppercase tracking-wide text-text-3">Accuracy</div><div className="text-lg font-semibold">{pct(perf.accuracy, 1)}</div></div>
          <div className="rounded-lg bg-surface-2 px-3 py-2"><div className="text-[10px] uppercase tracking-wide text-text-3">Calibration (ECE)</div><div className="text-lg font-semibold">{perf.ece.toFixed(3)}</div></div>
        </div>
        <div>
          <div className="mb-1 flex justify-between text-xs text-text-2"><span>Information captée vs marché</span><span className="tabular font-semibold">{pct(skill / mskill)}</span></div>
          <div className="h-2 rounded-full bg-surface-3"><div className="ai-gradient bar-grow h-full rounded-full" style={{ width: `${(skill / mskill) * 100}%` }} /></div>
          <p className="mt-1.5 text-[11px] leading-relaxed text-text-3">Skill score {pct(skill, 1)} contre {pct(mskill, 1)} pour les cotes, sans utiliser les cotes.</p>
        </div>
      </div>
    </Card>
  );
}

export function AIExplainer() {
  return (
    <Card className="p-4">
      <div className="flex items-start gap-3">
        <span className="ai-gradient grid size-9 shrink-0 place-items-center rounded-lg text-white"><BrainCircuit className="size-5" /></span>
        <div className="text-[13px] leading-relaxed text-text-2">
          <p className="font-semibold text-text">Lire une probabilité</p>
          <p className="mt-1">« 52 % » signifie que, sur un grand nombre de matchs comparables, l'issue s'est produite environ une fois sur deux. C'est une estimation, jamais une certitude.</p>
        </div>
      </div>
    </Card>
  );
}

/** Accès rapide à l'assistant et à la page Cotes & risque (colonne de droite de l'accueil). */
export function AssistantCard() {
  const { setOpen, send } = useAssistant();
  const ask = (q: string) => { setOpen(true); send(q); };
  return (
    <Card className="relative overflow-hidden p-4">
      <span className="ai-gradient absolute inset-x-0 top-0 h-0.5" aria-hidden />
      <div className="flex items-center gap-2"><span className="ai-gradient grid size-8 place-items-center rounded-lg text-white"><Sparkles className="size-4" /></span>
        <div><p className="text-[13px] font-semibold">Assistant statistique</p><p className="text-[11px] text-text-3">Posez une question sur un match ou une équipe</p></div></div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {["Matchs les moins risqués", "Le modèle est-il fiable ?"].map((q) => (
          <button key={q} onClick={() => ask(q)} className="rounded-full border border-border px-2.5 py-1 text-[12px] text-text-2 transition-colors hover:border-brand hover:text-brand">{q}</button>
        ))}
      </div>
      <Link href="/markets" className="mt-3 flex items-center gap-2 rounded-lg bg-surface-2 px-3 py-2 text-[12px] font-medium text-text-2 transition-colors hover:text-brand">
        <Scale className="size-4" />Cotes & risque : toutes les issues classées<ArrowUpRight className="ml-auto size-3.5" />
      </Link>
    </Card>
  );
}
