import type { Metadata } from "next";
import { MarketsView, type Disagreement } from "@/components/markets-view";
import { PageHeader } from "@/components/ui/primitives";
import { getCompetitions, getMarkets, getMatches, teamLite } from "@/lib/data";

export const metadata: Metadata = {
  title: "Cotes & risque",
  description: "Toutes les issues des prochains matchs classées par niveau de risque statistique, comparées aux probabilités implicites des cotes.",
  alternates: { canonical: "/markets" },
};

export default function MarketsPage() {
  const data = getMarkets();
  const matches = getMatches();
  const order = { "désaccord marqué": 0, "désaccord modéré": 1, accord: 2 } as const;
  const disagreements: Disagreement[] = matches
    .filter((m) => m.status === "scheduled" && m.prediction?.market && m.prediction.market.agreement !== "accord")
    .sort((a, b) => order[a.prediction!.market!.agreement] - order[b.prediction!.market!.agreement])
    .slice(0, 8)
    .map((m) => ({ slug: m.slug, homeName: m.homeName, awayName: m.awayName, home: m.home, away: m.away, kickoff: m.kickoff, competition: m.competition,
      market: m.prediction!.market!, model: [m.prediction!.home, m.prediction!.draw, m.prediction!.away] }));
  return (
    <>
      <PageHeader eyebrow="Analyse des cotes" title="Cotes & risque"
        subtitle="Chaque issue des prochains matchs, de la plus probable à la moins probable, avec la cote juste du modèle et, quand elle existe, la cote du marché." />
      <MarketsView data={data} competitions={getCompetitions()} disagreements={disagreements}
        teams={teamLite([...data.rows.flatMap((r) => [r.home, r.away]), ...disagreements.flatMap((d) => [d.home, d.away])])} />
    </>
  );
}
