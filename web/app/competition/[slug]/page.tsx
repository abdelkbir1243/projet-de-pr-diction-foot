import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Star, Users } from "lucide-react";
import { TabPanel, UrlTabs } from "@/components/ui/tabs";
import { Badge, Card, CardHeader, EmptyState, Stat } from "@/components/ui/primitives";
import { StandingsTable } from "@/components/standings";
import { MatchList } from "@/components/match-center";
import { Leaderboard } from "@/components/leaderboard";
import { FormIndicator, TeamLogo } from "@/components/football";
import { getCompetition, getCompetitionMatches, getCompetitions, getMeta, getStandings, getTeam, summarize, teamLite } from "@/lib/data";
import type { Team } from "@/lib/types";
import { pct } from "@/lib/utils";

export const dynamicParams = false;
export const generateStaticParams = () => getCompetitions().map((c) => ({ slug: c.slug }));

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const c = getCompetition((await params).slug);
  if (!c) return {};
  return { title: `${c.name} : classement, matchs et statistiques`, description: `${c.name} (${c.country}) ${c.season ?? ""} — classement, calendrier, statistiques d'équipes et prédictions IA.`, alternates: { canonical: `/competition/${c.slug}` } };
}

export default async function CompetitionPage({ params }: { params: Promise<{ slug: string }> }) {
  const c = getCompetition((await params).slug);
  if (!c) notFound();
  const rows = getStandings(c.slug);
  const matches = getCompetitionMatches(c.slug);
  const teams = c.teams.map((s) => getTeam(s)).filter(Boolean) as Team[];
  const lite = teamLite([...c.teams, ...matches.flatMap((m) => [m.home, m.away])]);
  const mode = getMeta().mode;
  const s = c.stats;
  return (
    <div className="space-y-4">
      <Card className="relative flex flex-wrap items-center gap-4 overflow-hidden p-5">
        <span aria-hidden className="ai-gradient pointer-events-none absolute -right-20 -top-24 size-64 rounded-full opacity-[0.12] blur-3xl" />
        <span className="ai-gradient absolute inset-x-0 top-0 h-0.5 opacity-70" aria-hidden />
        <span className="grid size-14 place-items-center rounded-2xl bg-text font-mono text-sm font-bold text-surface shadow-card">{c.cc}</span>
        <div className="min-w-0 flex-1">
          <div className="label-caps">Compétition</div>
          <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">{c.name}</h1>
          <p className="text-sm text-text-2">{c.country}{c.season ? ` · saison ${c.season}` : ""}{c.nTeams ? ` · ${c.nTeams} équipes` : ""}</p>
        </div>
        {c.covered ? <Badge tone="brand">Prédictions IA disponibles</Badge> : c.model === "cup" ? <Badge tone="brand">Prédictions IA · modèle coupes (Elo)</Badge> : <Badge tone="outline">Hors modèle de prédiction</Badge>}
      </Card>
      <Suspense>
        <UrlTabs defaultTab="overview" tabs={[{ value: "overview", label: "Aperçu" }, { value: "matches", label: "Matchs" }, { value: "standings", label: "Classement" },
          { value: "stats", label: "Statistiques" }, { value: "teams", label: "Équipes" }, { value: "players", label: "Meilleurs joueurs" }]}>
          <TabPanel value="overview">
            <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
              <div className="min-w-0 space-y-4">
                {s && (
                  <div className="snap-row -mx-3 px-3 sm:mx-0 sm:grid sm:grid-cols-4 sm:px-0 [&>*]:w-[44%] sm:[&>*]:w-auto">
                    <Stat label="Buts / match" value={s.goalsPerMatch.toFixed(2)} sub={`${s.matches} matchs`} />
                    <Stat label="Victoires à domicile" value={pct(s.homeWinPct)} sub={`nuls ${pct(s.drawPct)} · ext. ${pct(s.awayWinPct)}`} />
                    <Stat label="Plus de 2,5 buts" value={pct(s.over25Pct)} sub={`BTTS ${pct(s.bttsPct)}`} />
                    {s.cornersPerMatch != null ? <Stat label="Corners / match" value={s.cornersPerMatch.toFixed(1)} sub={`${(s.yellowPerMatch ?? 0).toFixed(1)} jaunes / match`} />
                      : <Stat label="Les deux marquent" value={pct(s.bttsPct)} sub={`${s.matches} matchs joués`} />}
                  </div>
                )}
                <Card><CardHeader title="Prochains matchs et résultats" action={<Link href="?tab=matches" scroll={false} className="text-xs font-medium text-brand hover:underline">Tous les matchs →</Link>} />
                  <MatchList matches={matches.slice(0, 12).map(summarize)} teams={lite} mode={mode} /></Card>
              </div>
              <Card><CardHeader title="Classement" action={<Link href="?tab=standings" scroll={false} className="text-xs font-medium text-brand hover:underline">Complet →</Link>} />
                {rows.length ? <StandingsTable rows={rows} comp={c} teams={lite} compact limit={8} /> : <EmptyState title="Classement non disponible" hint={c.model === "cup" ? "Phase à élimination directe ou format à groupes : pas de classement unique." : undefined} />}</Card>
            </div>
          </TabPanel>
          <TabPanel value="matches"><Card><MatchList matches={matches.map(summarize)} teams={lite} mode={mode} /></Card></TabPanel>
          <TabPanel value="standings"><Card>{rows.length ? <StandingsTable rows={rows} comp={c} teams={lite} /> : <EmptyState title="Classement non disponible" hint="Pas de phase de ligue pour cette saison dans nos données." />}</Card></TabPanel>
          <TabPanel value="stats">
            {teams.length ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <Leaderboard title="Meilleure attaque" subtitle="Buts marqués / match (10 derniers)" teams={teams} value={(t) => t.stats.goalsFor} fmt={(v) => v.toFixed(2)} />
                <Leaderboard title="Meilleure défense" subtitle="Buts encaissés / match" teams={teams} value={(t) => t.stats.goalsAgainst} fmt={(v) => v.toFixed(2)} asc />
                <Leaderboard title="Expected goals" subtitle="xG approché / match" teams={teams} value={(t) => t.stats.xgFor} fmt={(v) => v.toFixed(2)} />
                <Leaderboard title="Meilleure forme" subtitle="Points / match (10 derniers)" teams={teams} value={(t) => t.stats.ppg} fmt={(v) => v.toFixed(2)} />
                <Leaderboard title="Domination" subtitle="Part des tirs (proxy de possession)" teams={teams} value={(t) => t.stats.shotShare} fmt={(v) => `${Math.round(v * 100)} %`} />
                <Leaderboard title="Corners obtenus" subtitle="Par match" teams={teams} value={(t) => t.stats.corners} fmt={(v) => v.toFixed(1)} />
                <Leaderboard title="Cartons jaunes" subtitle="Par match" teams={teams} value={(t) => t.stats.yellow} fmt={(v) => v.toFixed(2)} />
                <Leaderboard title="Clean sheets" subtitle="% de matchs sans encaisser" teams={teams} value={(t) => t.stats.cleanSheetPct} fmt={(v) => `${Math.round(v * 100)} %`} />
                <Leaderboard title="Elo" subtitle="Niveau global (ClubElo)" teams={teams} value={(t) => t.elo} fmt={(v) => v.toFixed(0)} />
              </div>
            ) : <Card><EmptyState title="Statistiques non disponibles" /></Card>}
          </TabPanel>
          <TabPanel value="teams">
            {teams.length ? (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {teams.sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99)).map((t) => (
                  <Link key={t.slug} href={`/team/${t.slug}`}>
                    <Card interactive className="flex items-center gap-3 p-3">
                      <TeamLogo team={t} size={36} />
                      <div className="min-w-0 flex-1"><div className="truncate text-sm font-medium">{t.name}</div><div className="mt-1"><FormIndicator form={t.form} /></div></div>
                      <span className="tabular text-xs text-text-3">{t.rank}e</span>
                    </Card>
                  </Link>
                ))}
              </div>
            ) : <Card><EmptyState icon={<Users className="size-5" />} title="Liste des équipes non disponible" /></Card>}
          </TabPanel>
          <TabPanel value="players">
            <Card><EmptyState icon={<Star className="size-5" />} title="Statistiques joueurs bientôt disponibles"
              hint="Buteurs, passeurs et notes individuelles nécessitent une source de données joueurs. L'architecture est prête à l'accueillir." /></Card>
          </TabPanel>
        </UrlTabs>
      </Suspense>
    </div>
  );
}
