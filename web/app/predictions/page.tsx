import type { Metadata } from "next";
import { PredictionsView } from "@/components/predictions-view";
import { PageHeader } from "@/components/ui/primitives";
import { getCompetitions, getMatches, getPerformance, summarize, teamLite } from "@/lib/data";

export const metadata: Metadata = {
  title: "Prédictions IA",
  description: "Probabilités 1X2, score le plus probable, buts attendus, over 2,5 et BTTS pour les prochains matchs, avec l'historique des prédictions passées.",
  alternates: { canonical: "/predictions" },
};

export default function PredictionsPage() {
  const matches = getMatches();
  const hist = getPerformance().history;
  return (
    <>
      <PageHeader eyebrow="AI Predictions" title="Prédictions IA" subtitle="Probabilités calculées par un modèle statistique transparent. Ce sont des estimations, jamais des résultats garantis." />
      <PredictionsView matches={matches.map(summarize)} competitions={getCompetitions()} history={hist}
        teams={teamLite([...matches.flatMap((m) => [m.home, m.away]), ...hist.slice(0, 20).flatMap((h) => [h.home, h.away])])} />
    </>
  );
}
