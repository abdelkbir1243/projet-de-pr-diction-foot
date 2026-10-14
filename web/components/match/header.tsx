"use client";
/* En-tête du match : équipes, score ou heure, statut, compétition, date, stade, forme. */
import Link from "next/link";
import { CalendarClock, MapPin } from "lucide-react";
import type { Competition, LiveState, Match, Team, TeamLite } from "@/lib/types";
import { isLive } from "@/lib/status";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { AIBadge, FavoriteStar, FormGuide, MatchStatusBadge, TeamLogo } from "../football";
import { Badge, Card, CompetitionMark } from "../ui/primitives";

export function MatchHeader({ m, comp, teams, state, home, away }: { m: Match; comp: Competition; teams: Record<string, TeamLite>; state: LiveState; home: Team | null; away: Team | null }) {
  const { locale } = useI18n();
  const h = m.home ? teams[m.home] : null, a = m.away ? teams[m.away] : null;
  const live = isLive(state.status);
  const side = (team: TeamLite | null, full: Team | null, name: string, slug: string | null, align: "left" | "right") => {
    const inner = (
      <>
        <TeamLogo team={team} size={64} className="transition-transform duration-200 group-hover:scale-105 sm:size-[76px]" />
        <span className="mt-2 w-full truncate text-[15px] font-semibold sm:text-lg">{name}</span>
        {full && <span className="mt-1 hidden sm:block"><FormGuide items={full.form} /></span>}
        {full?.rank && <span className="mt-1 text-[11px] text-text-3">{full.rank}e · {full.points} pts</span>}
      </>
    );
    const cls = cn("group flex min-w-0 flex-col items-center text-center", align === "left" ? "sm:items-center" : "sm:items-center");
    return slug && team?.competition ? <Link href={`/team/${slug}`} className={cls}>{inner}</Link> : <div className={cls}>{inner}</div>;
  };
  return (
    <Card className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 opacity-[0.07]" aria-hidden
        style={{ background: `radial-gradient(60% 120% at 0% 0%, ${h?.color ?? "transparent"} 0%, transparent 60%), radial-gradient(60% 120% at 100% 0%, ${a?.color ?? "transparent"} 0%, transparent 60%)` }} />
      <div className="relative flex items-center justify-between px-3 pt-3 sm:px-4">
        <Link href={`/competition/${comp.slug}`} className="flex min-w-0 items-center gap-2 text-[12px] font-semibold uppercase tracking-[0.05em] text-text-2 hover:text-text">
          <CompetitionMark cc={comp.cc} /><span className="truncate">{comp.name}{m.round ? <span className="font-normal normal-case tracking-normal text-text-3"> · {m.round}</span> : null}</span>
          {m.extraTime && <Badge tone="outline">Prolongation · score à 90 min</Badge>}
        </Link>
        <div className="flex items-center gap-1">{m.prediction && <AIBadge label="AI Analysis" />}<FavoriteStar kind="matches" id={m.id} label={`${m.homeName} – ${m.awayName}`} /></div>
      </div>
      <div className="relative grid grid-cols-[1fr_auto_1fr] items-center gap-2 px-3 pb-5 pt-3 sm:gap-6 sm:px-10">
        {side(h, home, m.homeName, m.home, "left")}
        <div className="flex min-w-[96px] flex-col items-center gap-2">
          {state.score && state.status !== "scheduled" ? (
            <div className={cn("tabular text-[40px] font-semibold leading-none tracking-tight sm:text-5xl", live && "text-live")}>
              {state.score.home}<span className="mx-1.5 text-text-3">–</span>{state.score.away}
            </div>
          ) : (
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-text-3">vs</div>
          )}
          <MatchStatusBadge state={state} kickoff={m.kickoff} size="md" timeKnown={m.timeKnown !== false} />
        </div>
        {side(a, away, m.awayName, m.away, "right")}
      </div>
      <div className="relative flex flex-wrap items-center justify-center gap-x-5 gap-y-1 border-t border-border bg-surface-2/60 px-4 py-2 text-xs text-text-2">
        <span className="inline-flex items-center gap-1.5" suppressHydrationWarning><CalendarClock className="size-3.5" />{new Date(m.kickoff).toLocaleString(locale, m.timeKnown === false ? { weekday: "long", day: "numeric", month: "long" } : { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" })}</span>
        <span className="inline-flex items-center gap-1.5"><MapPin className="size-3.5" />{m.venue ?? "Stade non communiqué"}</span>
        {state.status === "postponed" && <Badge tone="warn">Match reporté — nouvelle date à confirmer</Badge>}
        {state.status === "cancelled" && <Badge tone="live">Match annulé</Badge>}
      </div>
    </Card>
  );
}
