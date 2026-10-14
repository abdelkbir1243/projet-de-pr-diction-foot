import type { Metadata } from "next";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Card, CardHeader, CompetitionMark, PageHeader } from "@/components/ui/primitives";
import { Leaderboard } from "@/components/leaderboard";
import { getCompetitions, getTeams } from "@/lib/data";
import { pct } from "@/lib/utils";

export const metadata: Metadata = { title: "Statistiques", description: "Comparaison des championnats et classements statistiques des équipes : attaque, défense, xG, corners, cartons.", alternates: { canonical: "/statistics" } };

export default function StatisticsPage() {
  const comps = getCompetitions().filter((c) => c.stats && c.stats.cornersPerMatch != null);
  const teams = getTeams();
  const cols: [string, (c: (typeof comps)[number]) => string][] = [
    ["Buts / match", (c) => c.stats!.goalsPerMatch.toFixed(2)], ["Vict. domicile", (c) => pct(c.stats!.homeWinPct)], ["Nuls", (c) => pct(c.stats!.drawPct)],
    ["Vict. extérieur", (c) => pct(c.stats!.awayWinPct)], ["+2,5 buts", (c) => pct(c.stats!.over25Pct)], ["BTTS", (c) => pct(c.stats!.bttsPct)],
    ["Corners / m", (c) => (c.stats!.cornersPerMatch ?? 0).toFixed(1)], ["Jaunes / m", (c) => (c.stats!.yellowPerMatch ?? 0).toFixed(1)],
  ];
  return (
    <>
      <PageHeader eyebrow="Data" title="Statistiques" subtitle="Ce qui s'est réellement passé sur le terrain : comparaison des championnats et meilleures équipes par indicateur.">
        <Link href="/ai-performance" className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-3 py-1.5 text-[13px] font-medium transition-colors hover:border-brand hover:text-brand">Performance du modèle <ArrowUpRight className="size-4" /></Link>
      </PageHeader>
      <Card className="mb-4">
        <CardHeader title="Comparaison des championnats" subtitle="Saison en cours (ou 380 derniers matchs en début de saison)" />
        <div className="scrollbar-thin overflow-x-auto">
          <table className="tabular w-full min-w-[720px] text-[13px]">
            <thead><tr className="border-b border-border text-[11px] uppercase tracking-wide text-text-3"><th className="sticky left-0 bg-surface py-2 pl-4 text-left font-medium">Championnat</th>{cols.map(([k]) => <th key={k} className="text-center font-medium">{k}</th>)}</tr></thead>
            <tbody>{comps.map((c) => (
              <tr key={c.slug} className="border-b border-border last:border-0 hover:bg-surface-2">
                <td className="sticky left-0 bg-surface py-2.5 pl-4 pr-2"><Link href={`/competition/${c.slug}?tab=stats`} className="flex items-center gap-2 whitespace-nowrap font-medium hover:text-brand"><CompetitionMark cc={c.cc} />{c.name}</Link></td>
                {cols.map(([k, f]) => <td key={k} className="text-center">{f(c)}</td>)}
              </tr>))}</tbody>
          </table>
        </div>
      </Card>
      <h2 className="label-caps mb-2">Top 5 européen · 10 derniers matchs</h2>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Leaderboard title="Meilleure attaque" subtitle="Buts / match" teams={teams} value={(t) => t.stats.goalsFor} fmt={(v) => v.toFixed(2)} />
        <Leaderboard title="Meilleure défense" subtitle="Buts encaissés / match" teams={teams} value={(t) => t.stats.goalsAgainst} fmt={(v) => v.toFixed(2)} asc />
        <Leaderboard title="Expected goals" subtitle="xG approché / match" teams={teams} value={(t) => t.stats.xgFor} fmt={(v) => v.toFixed(2)} />
        <Leaderboard title="Meilleure forme" subtitle="Points / match" teams={teams} value={(t) => t.stats.ppg} fmt={(v) => v.toFixed(2)} />
        <Leaderboard title="Domination" subtitle="Part des tirs (proxy de possession)" teams={teams} value={(t) => t.stats.shotShare} fmt={(v) => `${Math.round(v * 100)} %`} />
        <Leaderboard title="Elo" subtitle="Niveau global" teams={teams} value={(t) => t.elo} fmt={(v) => v.toFixed(0)} />
        <Leaderboard title="Corners obtenus" subtitle="Par match" teams={teams} value={(t) => t.stats.corners} fmt={(v) => v.toFixed(1)} />
        <Leaderboard title="Cartons jaunes" subtitle="Par match" teams={teams} value={(t) => t.stats.yellow} fmt={(v) => v.toFixed(2)} />
        <Leaderboard title="Matchs à +2,5 buts" subtitle="Part des matchs" teams={teams} value={(t) => t.stats.over25Pct} fmt={(v) => `${Math.round(v * 100)} %`} />
      </div>
    </>
  );
}
