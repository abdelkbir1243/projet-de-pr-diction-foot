"use client";
import Link from "next/link";
import type { Competition, StandingRow, TeamLite } from "@/lib/types";
import { cn } from "@/lib/utils";
import { FormIndicator, TeamLogo } from "./football";

function zoneOf(rank: number, z: Competition["zones"]) {
  if (z.cl && rank >= z.cl[0] && rank <= z.cl[1]) return "cl";
  if (z.el && rank >= z.el[0] && rank <= z.el[1]) return "el";
  if (z.rel && rank >= z.rel[0] && rank <= z.rel[1]) return "rel";
  return null;
}
const ZONE = { cl: "bg-[var(--zone-cl)]", el: "bg-[var(--zone-el)]", rel: "bg-[var(--zone-rel)]" } as const;

export function StandingsTable({ rows, comp, teams, highlight = [], compact = false, limit }: {
  rows: StandingRow[]; comp: Competition; teams: Record<string, TeamLite>; highlight?: (string | null)[]; compact?: boolean; limit?: number;
}) {
  const shown = limit ? rows.slice(0, limit) : rows;
  if (!rows.length) return <p className="px-4 py-8 text-center text-sm text-text-3">Classement indisponible pour cette compétition.</p>;
  return (
    <div>
      <div className="scrollbar-thin overflow-x-auto">
        <table className={"tabular w-full text-[13px]"}>
          <thead>
            <tr className="border-b border-border text-[11px] uppercase tracking-wide text-text-3">
              <th className="w-10 py-2 pl-4 text-left font-medium">#</th>
              <th className="py-2 text-left font-medium">Équipe</th>
              <th className="w-9 py-2 text-center font-medium">MJ</th>
              {!compact && ["V", "N", "D", "BP", "BC"].map((h) => <th key={h} className="hidden w-9 py-2 text-center font-medium sm:table-cell">{h}</th>)}
              <th className="w-11 py-2 text-center font-medium">Diff</th>
              <th className={cn("w-11 py-2 text-center font-semibold text-text-2", compact && "pr-4")}>Pts</th>
              {!compact && <th className="hidden py-2 pr-4 text-left font-medium md:table-cell">Forme</th>}
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => {
              const z = zoneOf(r.rank, comp.zones);
              const t = teams[r.team];
              return (
                <tr key={r.team} className={cn("border-b border-border last:border-0 transition-colors hover:bg-surface-2", highlight.includes(r.team) && "bg-brand-soft/60")}>
                  <td className="relative py-2 pl-4">
                    {z && <span className={cn("absolute inset-y-1 left-0 w-1 rounded-r", ZONE[z])} />}
                    <span className="text-text-2">{r.rank}</span>
                  </td>
                  <td className="py-2">
                    <Link href={`/team/${r.team}`} className="flex min-w-0 max-w-[160px] items-center gap-2 font-medium hover:text-brand sm:max-w-none">
                      <TeamLogo team={t} size={20} /><span className="truncate">{t?.name ?? r.team}</span>
                    </Link>
                  </td>
                  <td className="text-center text-text-2">{r.played}</td>{!compact && <><td className="hidden text-center sm:table-cell">{r.won}</td><td className="hidden text-center sm:table-cell">{r.drawn}</td><td className="hidden text-center sm:table-cell">{r.lost}</td></>}
                  {!compact && <><td className="hidden text-center text-text-2 sm:table-cell">{r.gf}</td><td className="hidden text-center text-text-2 sm:table-cell">{r.ga}</td></>}
                  <td className={cn("text-center", r.gd > 0 ? "text-good" : r.gd < 0 ? "text-bad" : "text-text-2")}>{r.gd > 0 ? `+${r.gd}` : r.gd}</td>
                  <td className={cn("text-center font-semibold", compact && "pr-4")}>{r.points}</td>
                  {!compact && <td className="hidden py-2 pr-4 md:table-cell"><FormIndicator form={r.form} /></td>}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {!compact && (
        <div className="flex flex-wrap gap-4 border-t border-border px-4 py-2.5 text-[11px] text-text-3">
          {comp.zones.cl && <Legend cls={ZONE.cl} label="Ligue des champions" />}
          {comp.zones.el && <Legend cls={ZONE.el} label="Ligue Europa" />}
          {comp.zones.rel && <Legend cls={ZONE.rel} label="Relégation" />}
          <span>Saison {comp.season} · classement calculé à partir des résultats disponibles</span>
        </div>
      )}
    </div>
  );
}
const Legend = ({ cls, label }: { cls: string; label: string }) => <span className="inline-flex items-center gap-1.5"><span className={cn("h-2.5 w-1 rounded", cls)} />{label}</span>;
