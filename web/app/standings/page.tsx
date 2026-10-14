import type { Metadata } from "next";
import { Suspense } from "react";
import { Card } from "@/components/ui/primitives";
import { PageHeader } from "@/components/ui/primitives";
import { TabPanel, UrlTabs } from "@/components/ui/tabs";
import { StandingsTable } from "@/components/standings";
import { getCompetitions, getStandings, teamLite } from "@/lib/data";

export const metadata: Metadata = { title: "Classements", description: "Classements des cinq grands championnats : zones européennes, relégation et forme sur les cinq derniers matchs.", alternates: { canonical: "/standings" } };

export default function StandingsPage() {
  const comps = getCompetitions().filter((c) => c.covered);
  const lite = teamLite();
  return (
    <>
      <PageHeader eyebrow="Saison en cours" title="Classements" subtitle="Zones Ligue des champions, Ligue Europa et relégation · forme sur les cinq derniers matchs." />
      <Suspense>
        <UrlTabs defaultTab={comps[0].slug} tabs={comps.map((c) => ({ value: c.slug, label: c.name }))}>
          {comps.map((c) => <TabPanel key={c.slug} value={c.slug}><Card><StandingsTable rows={getStandings(c.slug)} comp={c} teams={lite} /></Card></TabPanel>)}
        </UrlTabs>
      </Suspense>
    </>
  );
}
