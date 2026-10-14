"use client";
/* H2HCard : résumé des confrontations directes et liste des derniers matchs. */
import { Swords } from "lucide-react";
import type { H2H, TeamLite } from "@/lib/types";
import { useI18n } from "@/lib/i18n";
import { cn, pct } from "@/lib/utils";
import { ProbabilityBar, TeamLogo } from "../football";
import { Card, CardHeader, EmptyState, Stat } from "../ui/primitives";

export function H2HCard({ h2h, homeName, awayName, teams }: { h2h: H2H; homeName: string; awayName: string; teams: Record<string, TeamLite> }) {
  const { locale } = useI18n();
  const s = h2h.summary;
  if (!s) return <Card><EmptyState icon={<Swords className="size-5" />} title="Aucune confrontation récente" hint="Ces deux équipes ne se sont pas affrontées en championnat depuis 2005." /></Card>;
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="Head to Head" subtitle={`${s.n} dernières confrontations en championnat`} />
        <div className="px-4 pb-4">
          <div className="tabular grid grid-cols-3 items-end text-center">
            <div><div className="text-3xl font-semibold text-home">{s.homeWins}</div><div className="truncate text-xs text-text-3">Victoires {homeName}</div></div>
            <div><div className="text-3xl font-semibold text-text-2">{s.draws}</div><div className="text-xs text-text-3">Nuls</div></div>
            <div><div className="text-3xl font-semibold text-away">{s.awayWins}</div><div className="truncate text-xs text-text-3">Victoires {awayName}</div></div>
          </div>
          <div className="mt-3"><ProbabilityBar home={s.homeWins / s.n} draw={s.draws / s.n} away={s.awayWins / s.n} variant="mini" /></div>
        </div>
      </Card>
      <div className="snap-row sm:grid sm:grid-cols-4 sm:overflow-visible">
        <Stat className="min-w-[140px]" label="Moyenne de buts" value={s.avgGoals.toFixed(2)} />
        <Stat className="min-w-[140px]" label="Plus de 2,5 buts" value={pct(s.over25Pct)} bar={s.over25Pct} />
        <Stat className="min-w-[140px]" label="Les deux marquent" value={pct(s.bttsPct)} bar={s.bttsPct} />
        <Stat className="min-w-[140px]" label="Clean sheets" value={`${s.cleanSheetsHome} · ${s.cleanSheetsAway}`} sub={`${homeName} · ${awayName}`} />
      </div>
      <Card>
        <CardHeader title="Dernières confrontations" />
        <ul className="divide-y divide-border">
          {h2h.matches.map((x, i) => {
            const hw = x.homeGoals > x.awayGoals, aw = x.awayGoals > x.homeGoals;
            return (
              <li key={i} className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 px-3 py-2.5 text-[13px] sm:grid-cols-[76px_1fr_auto_1fr] sm:px-4">
                <span className="hidden text-xs text-text-3 sm:block">{new Date(x.date).toLocaleDateString(locale, { day: "2-digit", month: "short", year: "2-digit" })}</span>
                <span className={cn("flex min-w-0 items-center justify-end gap-2 text-right", hw ? "font-semibold" : "text-text-2")}><span className="truncate">{teams[x.home]?.name ?? x.home}</span><TeamLogo team={teams[x.home]} size={18} /></span>
                <span className={cn("tabular min-w-[52px] rounded-md px-2 py-0.5 text-center font-semibold", hw || aw ? "bg-surface-2" : "bg-surface-2 text-text-2")}>{x.homeGoals} – {x.awayGoals}</span>
                <span className={cn("flex min-w-0 items-center gap-2", aw ? "font-semibold" : "text-text-2")}><TeamLogo team={teams[x.away]} size={18} /><span className="truncate">{teams[x.away]?.name ?? x.away}</span></span>
              </li>
            );
          })}
        </ul>
      </Card>
    </div>
  );
}
