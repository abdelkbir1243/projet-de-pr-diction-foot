import { redirect } from "next/navigation";
import { getMatches } from "@/lib/data";

export const dynamicParams = false;
export function generateStaticParams() {
  return getMatches().filter((m) => m.prediction).map((m) => ({ slug: m.slug }));
}
export default async function PredictionRedirect({ params }: { params: Promise<{ slug: string }> }) {
  redirect(`/match/${(await params).slug}?tab=prediction`);
}
