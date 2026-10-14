import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/primitives";
import { PerformanceView } from "@/components/performance-view";
import { getPerformance, teamLite } from "@/lib/data";

export const metadata: Metadata = {
  title: "Performance IA — transparence du modèle",
  description: "Accuracy, log loss, Brier score, calibration et historique complet des prédictions du modèle, réussies et manquées, comparés aux cotes du marché.",
  alternates: { canonical: "/ai-performance" },
};

export default function AIPerformancePage() {
  const perf = getPerformance();
  return (
    <>
      <PageHeader eyebrow="Transparence du modèle" title="AI Performance" subtitle="Toutes les prédictions sont évaluées sur des matchs que le modèle n'avait jamais vus. Réussites et échecs sont affichés, comme la comparaison avec les cotes." />
      <PerformanceView perf={perf} teams={teamLite(perf.history.flatMap((h) => [h.home, h.away]))} />
    </>
  );
}
