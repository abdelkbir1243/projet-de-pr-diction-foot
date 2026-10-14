import type { Metadata } from "next";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Badge, Card, CompetitionMark, PageHeader } from "@/components/ui/primitives";
import { TeamLogo } from "@/components/football";
import { getCompetitions, getStandings, teamLite } from "@/lib/data";
import { pct } from "@/lib/utils";

export const metadata: Metadata = { title: "Compétitions", description: "Les principales compétitions européennes : classements, matchs, statistiques et équipes.", alternates: { canonical: "/competitions" } };

export default function CompetitionsPage() {
  const comps = getCompetitions();
  const teams = teamLite();
  return (
    <>
      <PageHeader eyebrow="Ligues" title="Compétitions" subtitle="Classements, calendriers et statistiques des principaux championnats européens." />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {comps.map((c) => {
          const top = getStandings(c.slug).slice(0, 3);
          return (
            <Link key={c.slug} href={`/competition/${c.slug}`} className="group">
              <Card interactive className="relative h-full overflow-hidden p-5">
                <span className="ai-gradient absolute inset-x-0 top-0 h-0.5 opacity-0 transition-opacity group-hover:opacity-80" aria-hidden />
                <div className="flex items-start justify-between">
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="grid size-11 place-items-center rounded-xl bg-text font-mono text-xs font-bold text-surface">{c.cc}</span>
                    <div className="min-w-0"><h2 className="truncate font-semibold">{c.name}</h2><p className="text-xs text-text-3">{c.country}{c.season ? ` · ${c.season}` : ""}</p></div>
                  </div>
                  <ArrowUpRight className="size-4 text-text-3 transition-colors group-hover:text-brand" />
                </div>
                {c.stats ? (
                  <dl className="tabular mt-4 grid grid-cols-3 gap-2 text-center">
                    <div className="rounded-lg bg-surface-2 py-2"><dt className="text-[10px] uppercase text-text-3">Buts/match</dt><dd className="font-semibold">{c.stats.goalsPerMatch.toFixed(2)}</dd></div>
                    <div className="rounded-lg bg-surface-2 py-2"><dt className="text-[10px] uppercase text-text-3">Vict. dom.</dt><dd className="font-semibold">{pct(c.stats.homeWinPct)}</dd></div>
                    <div className="rounded-lg bg-surface-2 py-2"><dt className="text-[10px] uppercase text-text-3">+2,5 buts</dt><dd className="font-semibold">{pct(c.stats.over25Pct)}</dd></div>
                  </dl>
                ) : <p className="mt-4 text-xs text-text-3">Calendrier et résultats. Compétition non couverte par le modèle de prédiction.</p>}
                {top.length > 0 && (
                  <ol className="mt-4 space-y-1.5 border-t border-border pt-3 text-[13px]">
                    {top.map((r) => <li key={r.team} className="flex items-center gap-2"><span className="w-4 text-text-3">{r.rank}</span><TeamLogo team={teams[r.team]} size={18} /><span className="flex-1 truncate">{teams[r.team]?.name}</span><span className="tabular font-semibold">{r.points}</span></li>)}
                  </ol>
                )}
                {c.model === "cup" ? <Badge tone="brand" className="mt-3">Modèle coupes (Elo)</Badge> : !c.covered && <Badge tone="outline" className="mt-3">Hors modèle</Badge>}
              </Card>
            </Link>
          );
        })}
      </div>
    </>
  );
}
