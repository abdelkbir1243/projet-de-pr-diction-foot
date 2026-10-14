import Link from "next/link";
import type { Team } from "@/lib/types";
import { TeamLogo } from "./football";
import { Card, CardHeader } from "./ui/primitives";

/** Classement d'équipes selon un indicateur (meilleure attaque, défense, etc.). */
export function Leaderboard({ title, subtitle, teams, value, fmt, asc = false, n = 5 }: {
  title: string; subtitle?: string; teams: Team[]; value: (t: Team) => number | null | undefined; fmt: (v: number) => string; asc?: boolean; n?: number;
}) {
  const rows = teams.filter((t) => value(t) != null).sort((a, b) => (asc ? 1 : -1) * ((value(a) as number) - (value(b) as number))).slice(0, n);
  const vals = rows.map((t) => Math.abs(value(t) as number));
  const max = Math.max(...vals, 1e-9), min = Math.min(...vals);
  return (
    <Card>
      <CardHeader title={title} subtitle={subtitle} />
      <ol className="space-y-2.5 p-4">
        {rows.map((t, i) => (
          <li key={t.slug} className="grid grid-cols-[16px_20px_1fr_auto] items-center gap-2 text-[13px]">
            <span className="text-xs text-text-3">{i + 1}</span>
            <TeamLogo team={t} size={20} />
            <Link href={`/team/${t.slug}`} className="group min-w-0">
              <div className="truncate font-medium group-hover:text-brand">{t.name}</div>
              <div className="mt-1 h-1 rounded-full bg-surface-3"><div className="bar-grow h-full rounded-full bg-brand" style={{ width: `${asc ? (Math.max(min, 0.05) / Math.max(Math.abs(value(t) as number), 0.05)) * 100 : (Math.abs(value(t) as number) / max) * 100}%` }} /></div>
            </Link>
            <span className="tabular font-semibold">{fmt(value(t) as number)}</span>
          </li>
        ))}
      </ol>
    </Card>
  );
}
