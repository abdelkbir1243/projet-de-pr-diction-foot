"use client";
/* Page match : orchestre l'en-tête et les onglets (Aperçu · Analyse IA · Stats · Cotes · H2H · Classement). */
import { Suspense } from "react";
import type { Competition, DataMode, LiveState, Match, MatchSummary, StandingRow, Team, TeamLite } from "@/lib/types";
import { liveState } from "@/lib/status";
import { useI18n } from "@/lib/i18n";
import { StandingsTable } from "./standings";
import { TabPanel, UrlTabs } from "./ui/tabs";
import { Card, CardHeader, EmptyState } from "./ui/primitives";
import { useLiveFeed, useNow } from "./live";
import { MatchHeader } from "./match/header";
import { Overview } from "./match/overview";
import { AIAnalysis } from "./match/ai-analysis";
import { TeamComparison } from "./match/team-comparison";
import { H2HCard } from "./match/h2h-card";
import { MarketCard, SimilarMatchesCard } from "./match/analysis-cards";

interface Props { m: Match; home: Team | null; away: Team | null; comp: Competition; standings: StandingRow[]; teams: Record<string, TeamLite>; mode: DataMode }

export function MatchDetail(p: Props) {
  const now = useNow(20_000);
  const { feed } = useLiveFeed(p.mode === "live", 30_000);
  const state: LiveState = now ? liveState({ ...p.m, prediction: null } as unknown as MatchSummary, now, feed[p.m.id]) : { status: p.m.status, minute: null, score: p.m.score };
  const { t } = useI18n();
  return (
    <div className="space-y-3">
      <MatchHeader m={p.m} comp={p.comp} teams={p.teams} state={state} home={p.home} away={p.away} />
      <Suspense>
        <UrlTabs defaultTab="overview" tabs={[
          { value: "overview", label: t("tabs.overview") }, { value: "prediction", label: t("tabs.prediction") }, { value: "stats", label: t("tabs.stats") },
          { value: "market", label: "Cotes" }, { value: "h2h", label: t("tabs.h2h") }, { value: "standings", label: t("tabs.standings") },
        ]}>
          <TabPanel value="overview"><Overview m={p.m} home={p.home} away={p.away} teams={p.teams} state={state} covered={p.comp.covered} /></TabPanel>
          <TabPanel value="prediction">
            <div className="space-y-4">
              <AIAnalysis m={p.m} home={p.home} away={p.away} teams={p.teams} />
              {p.m.prediction && <SimilarMatchesCard p={p.m.prediction} homeName={p.m.homeName} awayName={p.m.awayName} />}
            </div>
          </TabPanel>
          <TabPanel value="market"><MarketCard m={p.m} /></TabPanel>
          <TabPanel value="stats"><TeamComparison home={p.home} away={p.away} /></TabPanel>
          <TabPanel value="h2h"><H2HCard h2h={p.m.h2h} homeName={p.m.homeName} awayName={p.m.awayName} teams={p.teams} /></TabPanel>
          <TabPanel value="standings">
            <Card><CardHeader title={`Classement · ${p.comp.name}`} subtitle={p.comp.season ? `Saison ${p.comp.season}` : undefined} />
              {p.comp.covered ? <StandingsTable rows={p.standings} comp={p.comp} teams={p.teams} highlight={[p.m.home, p.m.away]} />
                : <EmptyState title="Classement non disponible" hint="Cette compétition n'est pas encore couverte par nos données historiques." />}
            </Card>
          </TabPanel>
        </UrlTabs>
      </Suspense>
    </div>
  );
}
