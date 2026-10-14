"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Sparkles } from "lucide-react";
import type { Competition, MatchSummary, Performance, TeamLite } from "@/lib/types";
import { useI18n } from "@/lib/i18n";
import { cn, dayKey, longDate } from "@/lib/utils";
import { isPrematchOpen, liveState } from "@/lib/status";
import { ProbabilityCard } from "./cards";
import { Card, CardHeader, CompetitionMark, EmptyState, Skeleton } from "./ui/primitives";
import { useNow } from "./live";
import { PredictionHistory } from "./prediction-history";

type Sort = "kickoff" | "confidence" | "uncertain";

export function PredictionsView({ matches, competitions, teams, history }: {
  matches: MatchSummary[]; competitions: Competition[]; teams: Record<string, TeamLite>; history: Performance["history"];
}) {
  const now = useNow(60_000);
  const { locale } = useI18n();
  const [comp, setComp] = useState<string>("all");
  const [sort, setSort] = useState<Sort>("kickoff");
  const upcoming = useMemo(() => {
    if (!now) return [];
    let l = matches.filter((m) => m.prediction && isPrematchOpen(m, now) && (comp === "all" || m.competition === comp));
    if (sort === "confidence") l = [...l].sort((a, b) => b.prediction!.confidence - a.prediction!.confidence);
    if (sort === "uncertain") l = [...l].sort((a, b) => Math.max(a.prediction!.home, a.prediction!.away) - Math.max(b.prediction!.home, b.prediction!.away));
    return l;
  }, [matches, now, comp, sort]);
  const byDay = useMemo(() => {
    const g = new Map<string, MatchSummary[]>();
    for (const m of upcoming) { const k = sort === "kickoff" ? dayKey(m.kickoff) : "all"; g.set(k, [...(g.get(k) ?? []), m]); }
    return [...g.entries()];
  }, [upcoming, sort]);
  const covered = competitions.filter((c) => c.covered || c.model === "cup");
  const recent = history.slice(0, 20);
  return (
    <div className="space-y-6">
      <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-center">
        <div className="snap-row -mx-3 min-w-0 flex-1 px-3 sm:mx-0 sm:px-0">
        <Chip on={comp === "all"} onClick={() => setComp("all")}>Toutes</Chip>
        {covered.map((c) => <Chip key={c.slug} on={comp === c.slug} onClick={() => setComp(c.slug)}><CompetitionMark cc={c.cc} size={16} />{c.name}</Chip>)}
        </div>
        <select value={sort} onChange={(e) => setSort(e.target.value as Sort)} aria-label="Trier"
          className="h-9 shrink-0 self-start rounded-lg border border-border bg-surface px-2 text-[13px] text-text-2">
          <option value="kickoff">Par date</option><option value="confidence">Plus forte confiance</option><option value="uncertain">Matchs les plus indécis</option>
        </select>
      </div>
      {!now ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-60 rounded-xl" />)}</div>
      ) : byDay.length === 0 ? (
        <Card><EmptyState icon={<Sparkles className="size-5" />} title="Aucune prédiction à venir pour ce filtre" hint="Les prédictions sont publiées plusieurs jours avant chaque journée de championnat." /></Card>
      ) : (
        byDay.map(([d, ms]) => (
          <section key={d} className="space-y-3">
            {d !== "all" && <h2 className="label-caps first-letter:uppercase">{longDate(d, locale)}</h2>}
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{ms.map((m) => <ProbabilityCard key={m.id} m={m} teams={teams} />)}</div>
          </section>
        ))
      )}
      <Card>
        <CardHeader title="Prédictions passées" subtitle="Prédictions hors échantillon et résultats réels — réussites ET échecs"
          action={<Link href="/ai-performance" className="text-xs font-medium text-brand hover:underline">Tout l'historique →</Link>} />
        <PredictionHistory rows={recent} teams={teams} />
      </Card>
    </div>
  );
}

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} className={cn("inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-full border px-3 text-[13px] font-medium transition-colors active:scale-95",
      on ? "border-brand bg-brand-soft text-brand-ink" : "border-border bg-surface text-text-2 hover:border-border-strong hover:text-text")}>{children}</button>
  );
}

/** Compatibilité : ancien nom. */
export { PredictionHistory as PredictionHistoryTable } from "./prediction-history";
