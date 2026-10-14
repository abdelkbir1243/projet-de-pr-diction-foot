import type { Metadata } from "next";
import { Chat } from "@/components/assistant";
import { Card, PageHeader } from "@/components/ui/primitives";

export const metadata: Metadata = {
  title: "Assistant statistique",
  description: "Posez vos questions sur un match, une équipe, un classement ou la fiabilité du modèle : réponses tirées des statistiques du site.",
  alternates: { canonical: "/assistant" },
};

export default function AssistantPage() {
  return (
    <>
      <PageHeader eyebrow="IA" title="Assistant statistique"
        subtitle="Il répond uniquement à partir des données publiées sur le site. Avec une clé ANTHROPIC_API_KEY configurée sur le serveur, Claude reformule ses réponses ; sans clé, un moteur local gratuit répond." />
      <Card className="mx-auto flex h-[calc(100dvh-260px)] min-h-[420px] max-w-3xl flex-col overflow-hidden"><Chat className="flex-1" /></Card>
    </>
  );
}
