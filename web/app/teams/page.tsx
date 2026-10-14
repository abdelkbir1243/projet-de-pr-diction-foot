import type { Metadata } from "next";
import Link from "next/link";
import { Card, CompetitionMark, PageHeader } from "@/components/ui/primitives";
import { FormIndicator, TeamLogo } from "@/components/football";
import { getCompetitions, getTeams } from "@/lib/data";

export const metadata: Metadata = { title: "Équipes", description: "Toutes les équipes des cinq grands championnats : forme, classement et statistiques.", alternates: { canonical: "/teams" } };

export default function TeamsPage() {
  const teams = getTeams();
  return (
    <>
      <PageHeader eyebrow="Clubs" title="Équipes" subtitle="Forme récente, classement et Elo de chaque club des cinq grands championnats." />
      <div className="space-y-6">
        {getCompetitions().filter((c) => c.covered).map((c) => (
          <section key={c.slug}>
            <h2 className="label-caps mb-2 flex items-center gap-2"><CompetitionMark cc={c.cc} />{c.name}</h2>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
              {teams.filter((t) => t.competition === c.slug).sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99)).map((t) => (
                <Link key={t.slug} href={`/team/${t.slug}`}>
                  <Card interactive className="flex items-center gap-3 p-3">
                    <TeamLogo team={t} size={32} />
                    <div className="min-w-0 flex-1"><div className="truncate text-sm font-medium">{t.name}</div><div className="mt-1"><FormIndicator form={t.form} /></div></div>
                    <div className="tabular text-right text-xs text-text-3"><div>{t.rank}e</div><div>Elo {t.elo}</div></div>
                  </Card>
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </>
  );
}
