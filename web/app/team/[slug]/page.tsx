import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Shirt } from "lucide-react";
import { TabPanel, UrlTabs } from "@/components/ui/tabs";
import { Card, CardHeader, EmptyState, Stat } from "@/components/ui/primitives";
import { FavoriteStar, FormIndicator, TeamLink, TeamLogo } from "@/components/football";
import { MatchList } from "@/components/match-center";
import { ProbabilityCard } from "@/components/cards";
import { PredictionHistory } from "@/components/prediction-history";
import { EloChart, TeamRadar } from "@/components/team-extras";
import { getCompetition, getMeta, getPerformance, getTeam, getTeamMatches, getTeams, summarize, teamLite } from "@/lib/data";
import { cn, num, pct } from "@/lib/utils";

export const dynamicParams = false;
export const generateStaticParams = () => getTeams().map((t) => ({ slug: t.slug }));

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const t = getTeam((await params).slug);
  if (!t) return {};
  const c = getCompetition(t.competition);
  return { title: `${t.name} : forme, statistiques et prédictions`, description: `${t.name} (${c?.name}) — ${t.rank ? `${t.rank}e, ${t.points} pts. ` : ""}Forme récente, statistiques détaillées, Elo et prédictions IA des prochains matchs.`, alternates: { canonical: `/team/${t.slug}` } };
}

export default async function TeamPage({ params }: { params: Promise<{ slug: string }> }) {
  const t = getTeam((await params).slug);
  if (!t) notFound();
  const comp = getCompetition(t.competition)!;
  const matches = getTeamMatches(t.slug);
  const mode = getMeta().mode;
  const ref = new Date(getMeta().now ?? getMeta().generatedAt).getTime();
  const upcomingPred = matches.filter((m) => m.prediction && new Date(m.kickoff).getTime() > ref);
  const hist = getPerformance().history.filter((h) => h.home === t.slug || h.away === t.slug);
  const lite = teamLite([t.slug, ...matches.flatMap((m) => [m.home, m.away]), ...t.lastMatches.map((r) => r.opponent), ...hist.flatMap((h) => [h.home, h.away])]);
  const s = t.stats;
  const jsonLd = { "@context": "https://schema.org", "@type": "SportsTeam", name: t.name, sport: "Football", memberOf: { "@type": "SportsOrganization", name: comp.name } };
  return (
    <div className="space-y-4">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <Card className="relative flex flex-wrap items-center gap-4 overflow-hidden p-5">
        <span aria-hidden className="pointer-events-none absolute -left-16 -top-24 size-64 rounded-full opacity-[0.14] blur-3xl" style={{ background: t.color }} />
        <span className="ai-gradient absolute inset-x-0 top-0 h-0.5 opacity-70" aria-hidden />
        <TeamLogo team={t} size={72} />
        <div className="min-w-0 flex-1">
          <div className="label-caps">Équipe</div><h1 className="text-xl font-semibold tracking-tight sm:text-2xl">{t.name}</h1>
          <p className="mt-0.5 text-sm text-text-2"><Link href={`/competition/${comp.slug}`} className="hover:text-brand">{comp.name}</Link> · {t.country}</p>
          <dl className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-text-3">
            <div>Stade : <span className="text-text-2">{t.stadium ?? "non communiqué"}</span></div>
            <div>Entraîneur : <span className="text-text-2">{t.coach ?? "non communiqué"}</span></div>
            <div>Elo : <span className="tabular text-text-2">{t.elo ?? "—"}</span></div>
          </dl>
        </div>
        <div className="flex w-full items-center gap-4 sm:w-auto">
          {t.rank && <div className="text-center"><div className="tabular text-2xl font-semibold">{t.rank}<span className="text-sm text-text-3">e</span></div><div className="text-[11px] text-text-3">{t.points} pts</div></div>}
          <div className="text-center"><FormIndicator form={t.form} size="md" /><div className="mt-1 text-[11px] text-text-3">Forme</div></div>
          <FavoriteStar kind="teams" id={t.slug} label={t.name} className="ml-auto size-10 border border-border sm:ml-0" />
        </div>
      </Card>
      <Suspense>
        <UrlTabs defaultTab="overview" tabs={[{ value: "overview", label: "Aperçu" }, { value: "matches", label: "Matchs" }, { value: "squad", label: "Effectif" },
          { value: "stats", label: "Statistiques" }, { value: "predictions", label: "Prédictions" }]}>
          <TabPanel value="overview">
            <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
              <div className="min-w-0 space-y-4">
                <div className="snap-row -mx-3 px-3 sm:mx-0 sm:grid sm:grid-cols-4 sm:px-0 [&>*]:w-[44%] sm:[&>*]:w-auto">
                  <Stat label="Points / match" value={num(s.ppg, 2)} sub={`${s.window} derniers matchs`} />
                  <Stat label="Buts marqués" value={num(s.goalsFor, 2)} sub={`xG ${num(s.xgFor, 2)}`} />
                  <Stat label="Buts encaissés" value={num(s.goalsAgainst, 2)} sub={`xG contre ${num(s.xgAgainst, 2)}`} />
                  <Stat label="Clean sheets" value={pct(s.cleanSheetPct)} sub={`+2,5 buts ${pct(s.over25Pct)}`} />
                </div>
                <Card><CardHeader title="Prochains matchs" /><MatchList matches={matches.filter((m) => new Date(m.kickoff).getTime() > ref - 3 * 3600e3).map(summarize)} teams={lite} mode={mode} /></Card>
                <Card><CardHeader title="Derniers résultats" />
                  <ul className="divide-y divide-border">
                    {t.lastMatches.map((r, i) => (
                      <li key={i} className="flex items-center gap-2.5 px-4 py-2.5 text-[13px] transition-colors hover:bg-surface-2">
                        <span className={cn("grid size-5 place-items-center rounded text-[10px] font-semibold text-white", r.result === "W" ? "bg-good" : r.result === "D" ? "bg-draw" : "bg-bad")}>{r.result === "W" ? "V" : r.result === "D" ? "N" : "D"}</span>
                        <span className="w-16 shrink-0 text-xs text-text-3 sm:w-20">{new Date(r.date).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "2-digit" })}</span>
                        <span className="hidden w-8 text-xs text-text-3 sm:inline">{r.venue === "home" ? "dom." : "ext."}</span>
                        <TeamLogo team={lite[r.opponent]} size={18} />
                        <TeamLink team={lite[r.opponent]} slug={r.opponent} className="min-w-0 flex-1 truncate">{r.opponentName}</TeamLink>
                        <span className="tabular font-semibold">{r.gf}–{r.ga}</span>
                      </li>
                    ))}
                  </ul>
                </Card>
              </div>
              <div className="space-y-4">
                <Card><CardHeader title="Profil statistique" subtitle="Percentiles au sein du championnat" /><div className="p-2"><TeamRadar team={t} /></div></Card>
                <Card><CardHeader title="Domicile / extérieur" subtitle="10 derniers matchs à domicile et à l'extérieur" />
                  <table className="tabular w-full text-[13px]"><thead><tr className="border-b border-border text-[11px] uppercase text-text-3"><th className="py-2 pl-4 text-left font-medium"></th><th className="font-medium">Pts/m</th><th className="font-medium">BP/m</th><th className="font-medium">BC/m</th><th className="pr-4 font-medium">% vict.</th></tr></thead>
                    <tbody>{([["Domicile", s.home], ["Extérieur", s.away]] as const).map(([k, b]) => (
                      <tr key={k} className="border-b border-border last:border-0 text-center"><td className="py-2 pl-4 text-left text-text-2">{k}</td><td>{num(b?.ppg, 2)}</td><td>{num(b?.gf, 2)}</td><td>{num(b?.ga, 2)}</td><td className="pr-4">{pct(b?.winPct)}</td></tr>
                    ))}</tbody></table>
                </Card>
              </div>
            </div>
          </TabPanel>
          <TabPanel value="matches"><Card><MatchList matches={matches.map(summarize)} teams={lite} mode={mode} emptyLabel="Aucun match programmé dans les prochains jours" /></Card></TabPanel>
          <TabPanel value="squad"><Card><EmptyState icon={<Shirt className="size-5" />} title="Effectif bientôt disponible" hint="Joueurs, postes, minutes et statistiques individuelles nécessitent une source de données joueurs ; l'interface est prête à les accueillir." /></Card></TabPanel>
          <TabPanel value="stats">
            <div className="grid gap-4 lg:grid-cols-2">
              <Card><CardHeader title="Évolution de l'Elo" subtitle="Niveau global au fil des matchs (ClubElo)" /><div className="p-3"><EloChart team={t} /></div></Card>
              <Card><CardHeader title="Statistiques détaillées" subtitle={`Moyennes par match · ${s.window} derniers matchs`} />
                <dl className="grid grid-cols-2 gap-x-6 gap-y-2 p-4 text-[13px]">
                  {[["Tirs", num(s.shots)], ["Tirs concédés", num(s.shotsAgainst)], ["Tirs cadrés", num(s.shotsOnTarget)], ["Part des tirs", pct(s.shotShare)],
                    ["xG (approché)", num(s.xgFor, 2)], ["xG concédés", num(s.xgAgainst, 2)], ["Corners", num(s.corners)], ["Corners concédés", num(s.cornersAgainst)],
                    ["Cartons jaunes", num(s.yellow, 2)], ["Cartons rouges", num(s.red, 2)], ["Fautes", num(s.fouls)], ["Les deux marquent", pct(s.bttsPct)]].map(([k, v]) => (
                    <div key={k} className="flex justify-between border-b border-border pb-1.5"><dt className="text-text-2">{k}</dt><dd className="tabular font-semibold">{v}</dd></div>
                  ))}
                </dl>
              </Card>
            </div>
          </TabPanel>
          <TabPanel value="predictions">
            <div className="space-y-4">
              {upcomingPred.length ? <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{upcomingPred.map((m) => <ProbabilityCard key={m.id} m={summarize(m)} teams={lite} />)}</div>
                : <Card><EmptyState title="Aucune prédiction à venir" hint="Les prédictions sont publiées quelques jours avant chaque match de championnat." /></Card>}
              <Card><CardHeader title={`Historique des prédictions · ${t.name}`} subtitle={`${hist.length} matchs évalués hors échantillon`} /><PredictionHistory rows={hist.slice(0, 25)} teams={lite} /></Card>
            </div>
          </TabPanel>
        </UrlTabs>
      </Suspense>
    </div>
  );
}
