import Link from "next/link";
import { SearchX } from "lucide-react";
import { Card, EmptyState } from "@/components/ui/primitives";

export default function NotFound() {
  return (
    <Card className="mx-auto mt-8 max-w-lg">
      <EmptyState icon={<SearchX className="size-5" />} title="Page introuvable" hint="Ce match, cette équipe ou cette compétition n'existe pas ou n'est plus disponible."
        action={<Link href="/" className="mt-2 rounded-lg bg-text px-3 py-1.5 text-[13px] font-medium text-surface">Retour aux matchs</Link>} />
    </Card>
  );
}
