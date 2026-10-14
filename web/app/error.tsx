"use client";
import { CloudOff } from "lucide-react";
import { Card, EmptyState } from "@/components/ui/primitives";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <Card className="mx-auto mt-8 max-w-lg">
      <EmptyState icon={<CloudOff className="size-5" />} title="Service momentanément indisponible" hint="Les données n'ont pas pu être chargées. Réessayez dans quelques instants."
        action={<button onClick={reset} className="mt-2 rounded-lg bg-text px-3 py-1.5 text-[13px] font-medium text-surface">Réessayer</button>} />
    </Card>
  );
}
