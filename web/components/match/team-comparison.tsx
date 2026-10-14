"use client";
/* TeamComparison : barres comparatives centrées (domicile à gauche, extérieur à droite), la meilleure valeur mise en évidence. */
import type { Team } from "@/lib/types";
import { cn } from "@/lib/utils";
import { TeamLogo } from "../football";
import { Card, CardHeader, EmptyState } from "../ui/primitives";

export interface CompareRow { label: string; home: number | null | undefined; away: number | null | undefined; fmt: (v: number) => string; better?: "high" | "low" | null }

export function teamCompareRows(h: Team, a: Team): CompareRow[] {
  const pctf = (v: number) => `${Math.round(v * 100)} %`;
  return [
    { label: "Buts / match", home: h.stats.goalsFor, away: a.stats.goalsFor, fmt: (v) => v.toFixed(2), better: "high" },
    { label: "Buts encaissés", home: h.stats.goalsAgainst, away: a.stats.goalsAgainst, fmt: (v) => v.toFixed(2), better: "low" },
    { label: "Possession*", home: h.stats.shotShare, away: a.stats.shotShare, fmt: pctf, better: "high" },
    { label: "xG", home: h.stats.xgFor, away: a.stats.xgFor, fmt: (v) => v.toFixed(2), better: "high" },
    { label: "xG concédés", home: h.stats.xgAgainst, away: a.stats.xgAgainst, fmt: (v) => v.toFixed(2), better: "low" },
    { label: "Tirs / match", home: h.stats.shots, away: a.stats.shots, fmt: (v) => v.toFixed(1), better: "high" },
    { label: "Tirs cadrés", home: h.stats.shotsOnTarget, away: a.stats.shotsOnTarget, fmt: (v) => v.toFixed(1), better: "high" },
    { label: "Corners / match", home: h.stats.corners, away: a.stats.corners, fmt: (v) => v.toFixed(1), better: "high" },
    { label: "Points / match", home: h.stats.ppg, away: a.stats.ppg, fmt: (v) => v.toFixed(2), better: "high" },
    { label: "Clean sheets", home: h.stats.cleanSheetPct, away: a.stats.cleanSheetPct, fmt: pctf, better: "high" },
    { label: "Cartons jaunes", home: h.stats.yellow, away: a.stats.yellow, fmt: (v) => v.toFixed(1), better: null },
  ];
}

export function CompareBar({ row }: { row: CompareRow }) {
  const { home: h, away: a } = row;
  if (h == null || a == null) return null;
  const tot = Math.abs(h) + Math.abs(a) || 1;
  const hb = row.better && (row.better === "high" ? h > a : h < a);
  const ab = row.better && (row.better === "high" ? a > h : a < h);
  return (
    <div className="py-2">
      <div className="tabular mb-1.5 grid grid-cols-[1fr_auto_1fr] items-baseline gap-2 text-[13px]">
        <span className={cn("font-semibold", hb ? "text-home" : "text-text-2")}>{row.fmt(h)}</span>
        <span className="text-center text-xs text-text-3">{row.label}</span>
        <span className={cn("text-right font-semibold", ab ? "text-away" : "text-text-2")}>{row.fmt(a)}</span>
      </div>
      <div className="flex h-1.5 gap-1">
        <div className="flex flex-1 justify-end overflow-hidden rounded-full bg-surface-3"><div className={cn("bar-grow-r h-full rounded-full", hb ? "bg-home" : "bg-home/40")} style={{ width: `${(Math.abs(h) / tot) * 100}%` }} /></div>
        <div className="flex-1 overflow-hidden rounded-full bg-surface-3"><div className={cn("bar-grow h-full rounded-full", ab ? "bg-away" : "bg-away/40")} style={{ width: `${(Math.abs(a) / tot) * 100}%` }} /></div>
      </div>
    </div>
  );
}

export function TeamComparison({ home, away, title = "Team Comparison", limit }: { home: Team | null; away: Team | null; title?: string; limit?: number }) {
  if (!home || !away) return <Card><EmptyState title="Comparaison indisponible" /></Card>;
  const rows = teamCompareRows(home, away).slice(0, limit);
  return (
    <Card>
      <CardHeader title={title} subtitle={`10 derniers matchs de championnat · saison ${home.stats.season.label}`} />
      <div className="px-4 pb-2">
        <div className="mb-1 flex items-center justify-between border-b border-border pb-2.5">
          <span className="flex min-w-0 items-center gap-2"><TeamLogo team={home} size={22} /><span className="truncate text-[13px] font-semibold text-home">{home.name}</span></span>
          <span className="flex min-w-0 flex-row-reverse items-center gap-2"><TeamLogo team={away} size={22} /><span className="truncate text-[13px] font-semibold text-away">{away.name}</span></span>
        </div>
        <div className="divide-y divide-border/60">{rows.map((r) => <CompareBar key={r.label} row={r} />)}</div>
      </div>
      <p className="border-t border-border px-4 py-2 text-[11px] text-text-3">* Part des tirs (proxy : la possession n'est pas fournie par nos sources). xG approché = tirs cadrés × taux de conversion de la ligue.</p>
    </Card>
  );
}
