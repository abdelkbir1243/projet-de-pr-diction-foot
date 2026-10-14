import { MatchCenter } from "@/components/match-center";
import { AIExplainer, AIPerformanceMini, AssistantCard, ProbabilityCard } from "@/components/cards";
import { getCompetitions, getDays, getMatches, getMeta, getPerformance, summarize, teamLite } from "@/lib/data";

/** Match Center : page d'accueil et /matches. */
export function HomeView() {
  const meta = getMeta();
  const matches = getMatches();
  const teams = teamLite(matches.flatMap((m) => [m.home, m.away]));
  const perf = getPerformance();
  const featured = matches
    .filter((m) => m.prediction && m.status === "scheduled")
    .sort((a, b) => Math.max(b.prediction!.home, b.prediction!.away) - Math.max(a.prediction!.home, a.prediction!.away))
    .slice(0, 3);
  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0">
        <h1 className="sr-only">Matchs du jour et prédictions IA</h1>
        <MatchCenter matches={matches.map(summarize)} competitions={getCompetitions()} teams={teams} mode={meta.mode} days={getDays()} />
      </div>
      <aside className="min-w-0 space-y-4" aria-label="Prédictions à la une">
        <h2 className="label-caps">À la une · IA</h2>
        <AssistantCard />
        {featured.map((m) => <ProbabilityCard key={m.id} m={summarize(m)} teams={teams} />)}
        <AIPerformanceMini perf={perf} />
        <AIExplainer />
      </aside>
    </div>
  );
}
