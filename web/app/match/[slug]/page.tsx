import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { MatchDetail } from "@/components/match-detail";
import { getCompetition, getMatch, getMatches, getMeta, getStandings, getTeam, teamLite } from "@/lib/data";

export const dynamicParams = false;
export function generateStaticParams() {
  return getMatches().map((m) => ({ slug: m.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const m = getMatch((await params).slug);
  if (!m) return {};
  const comp = getCompetition(m.competition);
  const p = m.prediction;
  const title = `${m.homeName} – ${m.awayName} : analyse et probabilités`;
  const description = p
    ? `${comp?.name} · ${m.homeName} ${Math.round(p.home * 100)} %, nul ${Math.round(p.draw * 100)} %, ${m.awayName} ${Math.round(p.away * 100)} %. Buts attendus ${p.xg.total.toFixed(1)}, forme, H2H et statistiques.`
    : `${comp?.name} · ${m.homeName} – ${m.awayName} : forme, confrontations et statistiques.`;
  return { title, description, alternates: { canonical: `/match/${m.slug}` }, openGraph: { title, description, type: "article" } };
}

export default async function MatchPage({ params }: { params: Promise<{ slug: string }> }) {
  const m = getMatch((await params).slug);
  if (!m) notFound();
  const comp = getCompetition(m.competition)!;
  const standings = getStandings(comp.slug);
  const slugs = [m.home, m.away, ...standings.map((r) => r.team), ...m.h2h.matches.flatMap((x) => [x.home, x.away]),
    ...[getTeam(m.home), getTeam(m.away)].flatMap((t) => t?.lastMatches.map((r) => r.opponent) ?? [])];
  const jsonLd = {
    "@context": "https://schema.org", "@type": "SportsEvent", name: `${m.homeName} – ${m.awayName}`, startDate: m.kickoff, sport: "Football",
    eventStatus: m.status === "postponed" ? "https://schema.org/EventPostponed" : m.status === "cancelled" ? "https://schema.org/EventCancelled" : "https://schema.org/EventScheduled",
    homeTeam: { "@type": "SportsTeam", name: m.homeName }, awayTeam: { "@type": "SportsTeam", name: m.awayName },
    superEvent: { "@type": "SportsEvent", name: comp.name },
  };
  return (
    <article>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <h1 className="sr-only">{m.homeName} – {m.awayName}</h1>
      <MatchDetail m={m} home={getTeam(m.home)} away={getTeam(m.away)} comp={comp} standings={standings} teams={teamLite(slugs)} mode={getMeta().mode} />
    </article>
  );
}
