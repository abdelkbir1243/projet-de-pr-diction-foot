"use client";
/* Match Center : DateSelector, filtres, LeagueHeader, MatchCard, MatchList, squelettes. */
import Link from "next/link";
import { useMemo, useState } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, CloudOff, Radio, Sparkles, Trophy } from "lucide-react";
import type { Competition, DataMode, DaySummary, LiveState, MatchSummary, TeamLite } from "@/lib/types";
import { DaySummaryCard } from "./day-summary";
import { LevelChip } from "./confidence";
import { liveState, isLive } from "@/lib/status";
import { useI18n, type TKey } from "@/lib/i18n";
import { addDays, cn, dayKey, longDate } from "@/lib/utils";
import { AIBadge, FavoriteStar, MatchStatusBadge, ProbabilityBar, TeamLogo } from "./football";
import { Badge, CompetitionMark, EmptyState, Skeleton } from "./ui/primitives";
import { useLiveFeed, useNow } from "./live";

type Filter = "all" | "live" | "upcoming" | "finished" | "predicted";
const FILTERS: { v: Filter; k: TKey }[] = [
  { v: "all", k: "filter.all" }, { v: "live", k: "filter.live" }, { v: "upcoming", k: "filter.upcoming" },
  { v: "finished", k: "filter.finished" }, { v: "predicted", k: "filter.predicted" },
];

/* ───────────────────────────── DateSelector : ← HIER | AUJOURD'HUI | DEMAIN 📅 → ───────────────────────────── */
export function DateSelector({ value, onChange, today }: { value: string; onChange: (d: string) => void; today: string }) {
  const { t, locale } = useI18n();
  const rel = (d: string) => (d === today ? t("date.today") : d === addDays(today, -1) ? t("date.yesterday") : d === addDays(today, 1) ? t("date.tomorrow") : null);
  const days = [-1, 0, 1].map((k) => addDays(value, k));
  const nav = "grid size-9 shrink-0 sm:size-10 place-items-center rounded-lg text-text-2 transition-colors hover:bg-surface-2 hover:text-text";
  return (
    <div className="flex min-w-0 items-center gap-0.5 rounded-xl border border-border bg-surface p-1 shadow-card sm:gap-1">
      <button className={nav} onClick={() => onChange(addDays(value, -1))} aria-label="Jour précédent"><ChevronLeft className="size-4" /></button>
      <div className="grid min-w-0 flex-1 grid-cols-[repeat(3,minmax(0,1fr))] gap-1">
        {days.map((d) => {
          const on = d === value;
          return (
            <button key={d} onClick={() => onChange(d)} aria-pressed={on}
              className={cn("min-w-0 rounded-lg px-1 py-1.5 text-center transition-all", on ? "bg-text text-surface shadow-card" : "text-text-2 hover:bg-surface-2")}>
              <div className="truncate text-[11px] font-semibold uppercase leading-tight tracking-wide sm:text-[12px]">
                {rel(d) ?? new Date(d + "T12:00").toLocaleDateString(locale, { weekday: "short" })}
              </div>
              <div className={cn("text-[11px] leading-tight", on ? "opacity-70" : "text-text-3")}>
                {new Date(d + "T12:00").toLocaleDateString(locale, { day: "numeric", month: "short" })}
              </div>
            </button>
          );
        })}
      </div>
      <label className={cn(nav, "relative cursor-pointer")} title={t("date.pick")}>
        <CalendarDays className="size-4" />
        <input type="date" value={value} onChange={(e) => e.target.value && onChange(e.target.value)} className="absolute inset-0 cursor-pointer opacity-0" aria-label={t("date.pick")} />
      </label>
      <button className={nav} onClick={() => onChange(addDays(value, 1))} aria-label="Jour suivant"><ChevronRight className="size-4" /></button>
    </div>
  );
}

/* ───────────────────────────── MatchCard ─────────────────────────────
   Carte entièrement cliquable (lien étiré) ; l'étoile reste un bouton indépendant (pas de bouton dans un lien). */
export function MatchCard({ m, state, teams }: { m: MatchSummary; state: LiveState; teams: Record<string, TeamLite> }) {
  const { t } = useI18n();
  const h = m.home ? teams[m.home] : null, a = m.away ? teams[m.away] : null;
  const showScore = state.score && state.status !== "scheduled";
  const winner = state.status === "finished" && state.score ? Math.sign(state.score.home - state.score.away) : null;
  const live = isLive(state.status);
  const p = m.prediction;
  const row = (team: TeamLite | null, name: string, goals: number | undefined, side: 1 | -1) => (
    <div className="flex min-w-0 items-center gap-2.5">
      <TeamLogo team={team} size={22} />
      <span className={cn("min-w-0 flex-1 truncate text-[14px]", winner === -side ? "text-text-3" : "font-medium text-text")}>{name}</span>
      {showScore && <span className={cn("tabular w-5 text-right text-[15px] font-semibold", live ? "text-live" : winner === -side ? "text-text-3" : "text-text")}>{goals}</span>}
    </div>
  );
  return (
    <div className={cn("group relative grid grid-cols-[48px_minmax(0,1fr)_auto] items-center gap-x-3 px-3 py-2.5 transition-colors hover:bg-surface-2/70 sm:grid-cols-[64px_minmax(0,1fr)_184px_auto] sm:px-4",
      live && "bg-live-soft/30", state.status === "cancelled" && "opacity-60")}>
      {live && <span className="absolute inset-y-2 left-0 w-0.5 rounded-r bg-live" aria-hidden />}
      <div className="flex flex-col items-start gap-1">
        <MatchStatusBadge state={state} kickoff={m.kickoff} timeKnown={m.timeKnown !== false} />
        {p && <span className="sm:hidden">{p.level ? <LevelChip level={p.level} /> : <AIBadge />}</span>}
      </div>
      <div className="min-w-0 space-y-1.5">
        {row(h, m.homeName, state.score?.home, 1)}
        {row(a, m.awayName, state.score?.away, -1)}
        {p && <div className="pt-0.5 sm:hidden"><ProbabilityBar home={p.home} draw={p.draw} away={p.away} variant="compact" animate={false} /></div>}
      </div>
      <div className="hidden sm:block">
        {p ? (
          <div>
            <div className="mb-1 flex items-center justify-between"><AIBadge />{p.level ? <LevelChip level={p.level} /> : <span className="text-[10px] text-text-3">{t("match.confidence").split(" ")[0]} {Math.round(p.confidence * 100)} %</span>}</div>
            <ProbabilityBar home={p.home} draw={p.draw} away={p.away} variant="compact" animate={false} />
          </div>
        ) : <span className="text-[11px] text-text-3">{t("match.noPrediction")}</span>}
      </div>
      <FavoriteStar kind="matches" id={m.id} label={`${m.homeName} – ${m.awayName}`} />
      <Link href={`/match/${m.slug}`} className="absolute inset-0 rounded-[inherit] focus-visible:outline-offset-[-2px]" aria-label={`${m.homeName} contre ${m.awayName} — voir l'analyse`} />
    </div>
  );
}

/* ───────────────────────────── LeagueHeader + section ───────────────────────────── */
export function LeagueHeader({ comp, count, liveCount }: { comp: Competition; count?: number; liveCount?: number }) {
  return (
    <header className="flex items-center justify-between gap-2 border-b border-border px-3 py-2.5 sm:px-4">
      <Link href={`/competition/${comp.slug}`} className="flex min-w-0 items-center gap-2.5 hover:opacity-80">
        <CompetitionMark cc={comp.cc} />
        <span className="min-w-0">
          <span className="block truncate text-[13px] font-semibold uppercase tracking-[0.04em] text-text">{comp.name}</span>
          <span className="block truncate text-[11px] text-text-3">{comp.country}{comp.season ? ` · ${comp.season}` : ""}</span>
        </span>
      </Link>
      <div className="flex shrink-0 items-center gap-1.5">
        {!!liveCount && <Badge tone="live"><span className="size-1.5 animate-pulse-dot rounded-full bg-live" />{liveCount} live</Badge>}
        {!comp.covered && comp.model !== "cup" ? <Badge tone="outline">Hors modèle IA</Badge> : count != null && <span className="tabular text-xs text-text-3">{count}</span>}
      </div>
    </header>
  );
}

export function LeagueSection({ comp, matches, states, teams }: { comp: Competition; matches: MatchSummary[]; states: Map<string, LiveState>; teams: Record<string, TeamLite> }) {
  const liveCount = matches.filter((m) => isLive(states.get(m.id)!.status)).length;
  return (
    <section className="animate-fade-in overflow-hidden rounded-xl border border-border bg-surface shadow-card">
      <LeagueHeader comp={comp} count={matches.length} liveCount={liveCount} />
      <div className="divide-y divide-border">{matches.map((m) => <MatchCard key={m.id} m={m} state={states.get(m.id)!} teams={teams} />)}</div>
    </section>
  );
}

/* ───────────────────────────── MatchCenter ───────────────────────────── */
export function MatchCenter({ matches, competitions, teams, mode, days = {} }: { matches: MatchSummary[]; competitions: Competition[]; teams: Record<string, TeamLite>; mode: DataMode; days?: Record<string, DaySummary> }) {
  const { t, locale } = useI18n();
  const now = useNow(30_000);
  const { feed, error } = useLiveFeed(mode === "live");
  const [date, setDate] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const today = now ? dayKey(new Date(now)) : null;
  // jour affiché par défaut : aujourd'hui s'il y a des matchs, sinon le jour de match le plus proche (à venir de préférence)
  const nearest = useMemo(() => {
    if (!today) return null;
    const days = [...new Set(matches.map((m) => dayKey(m.kickoff)))].sort();
    if (!days.length || days.includes(today)) return today;
    return days.find((d) => d > today) ?? days[days.length - 1];
  }, [matches, today]);
  const day = date ?? nearest;

  const states = useMemo(() => {
    const s = new Map<string, LiveState>();
    if (now) for (const m of matches) s.set(m.id, liveState(m, now, feed[m.id]));
    return s;
  }, [matches, now, feed]);
  const ofDay = useMemo(() => (day ? matches.filter((m) => dayKey(m.kickoff) === day) : []), [matches, day]);
  const counts = useMemo(() => {
    const c: Record<Filter, number> = { all: ofDay.length, live: 0, upcoming: 0, finished: 0, predicted: 0 };
    for (const m of ofDay) {
      const st = states.get(m.id)?.status;
      if (st && isLive(st)) c.live++; if (st === "scheduled") c.upcoming++; if (st === "finished") c.finished++; if (m.prediction) c.predicted++;
    }
    return c;
  }, [ofDay, states]);
  const keep = (m: MatchSummary) => {
    const st = states.get(m.id)?.status;
    return filter === "all" || (filter === "live" && !!st && isLive(st)) || (filter === "upcoming" && st === "scheduled") || (filter === "finished" && st === "finished") || (filter === "predicted" && !!m.prediction);
  };
  const shown = ofDay.filter(keep);
  // ordre : compétitions avec un match en direct d'abord, puis ordre éditorial
  const groups = competitions.map((c) => ({ c, ms: shown.filter((m) => m.competition === c.slug) })).filter((g) => g.ms.length)
    .sort((x, y) => Number(y.ms.some((m) => isLive(states.get(m.id)!.status))) - Number(x.ms.some((m) => isLive(states.get(m.id)!.status))));

  if (!now || !day) return <MatchCenterSkeleton />;
  return (
    <div className="space-y-3">
      <DateSelector value={day} onChange={setDate} today={today!} />
      <div className="snap-row -mx-3 px-3 sm:mx-0 sm:px-0" role="tablist" aria-label="Filtres">
        {FILTERS.map((f) => (
          <button key={f.v} role="tab" aria-selected={filter === f.v} onClick={() => setFilter(f.v)}
            className={cn("inline-flex h-9 items-center gap-1.5 rounded-full border px-3.5 text-[13px] font-medium transition-colors",
              filter === f.v ? "border-transparent bg-text text-surface" : "border-border bg-surface text-text-2 hover:border-border-strong hover:text-text")}>
            {f.v === "live" && <span className={cn("size-1.5 rounded-full", counts.live ? "animate-pulse-dot bg-live" : "bg-text-3")} />}
            {f.v === "predicted" && <Sparkles className={cn("size-3.5", filter !== f.v && "text-brand")} />}
            {t(f.k)}
            <span className={cn("tabular rounded-full px-1.5 text-[11px]", filter === f.v ? "bg-surface/20" : "bg-surface-2 text-text-3")}>{counts[f.v]}</span>
          </button>
        ))}
      </div>
      {mode === "live" && error && (
        <div className="flex items-center gap-2 rounded-lg border border-warn/30 bg-warn-soft px-3 py-2 text-xs text-warn" role="status">
          <CloudOff className="size-4 shrink-0" /> Scores en direct momentanément indisponibles : affichage des dernières données connues.
        </div>
      )}
      <h2 className="sr-only">{longDate(day, locale)}</h2>
      {days[day] && filter === "all" && <DaySummaryCard day={days[day]} label={longDate(day, locale)} />}
      {groups.length ? groups.map(({ c, ms }) => <LeagueSection key={c.slug} comp={c} matches={ms} states={states} teams={teams} />) : (
        <div className="rounded-xl border border-dashed border-border-strong bg-surface">
          <EmptyState icon={filter === "live" ? <Radio className="size-5" /> : <Trophy className="size-5" />}
            title={ofDay.length ? (filter === "live" ? "Aucun match en direct pour le moment" : t("empty.filter")) : t("empty.noMatches")}
            hint={ofDay.length ? undefined : `${longDate(day, locale)} — ${t("empty.noMatchesHint")}`}
            action={filter !== "all" ? <button onClick={() => setFilter("all")} className="mt-1 text-xs font-medium text-brand hover:underline">{t("filter.all")}</button> : undefined} />
        </div>
      )}
    </div>
  );
}

export function MatchCenterSkeleton() {
  return (
    <div className="space-y-3" aria-busy aria-label="Chargement des matchs">
      <Skeleton className="h-[54px] rounded-xl" />
      <div className="flex gap-2 overflow-hidden">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-9 w-28 shrink-0 rounded-full" />)}</div>
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="overflow-hidden rounded-xl border border-border bg-surface">
          <div className="flex items-center gap-2 border-b border-border px-4 py-3"><Skeleton className="h-5 w-7" /><Skeleton className="h-4 w-36" /></div>
          {Array.from({ length: 3 }).map((_, j) => (
            <div key={j} className="grid grid-cols-[48px_1fr] items-center gap-3 px-4 py-3 sm:grid-cols-[64px_1fr_184px]">
              <Skeleton className="h-3.5 w-10" />
              <div className="space-y-2"><Skeleton className="h-4 w-40" /><Skeleton className="h-4 w-32" /></div>
              <Skeleton className="hidden h-2 sm:block" />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

/* ───────────────────────────── MatchList (pages compétition / équipe) ───────────────────────────── */
export function MatchList({ matches, teams, mode, emptyLabel = "Aucun match programmé" }: { matches: MatchSummary[]; teams: Record<string, TeamLite>; mode: DataMode; emptyLabel?: string }) {
  const now = useNow(30_000);
  const { feed } = useLiveFeed(mode === "live");
  const { locale } = useI18n();
  if (!now) return <div className="space-y-2 p-4">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-12" />)}</div>;
  if (!matches.length) return <EmptyState icon={<CalendarDays className="size-5" />} title={emptyLabel} />;
  const groups = new Map<string, MatchSummary[]>();
  for (const m of matches) { const k = dayKey(m.kickoff); groups.set(k, [...(groups.get(k) ?? []), m]); }
  return (
    <div>
      {[...groups.entries()].map(([d, ms]) => (
        <div key={d}>
          <div className="border-y border-border bg-surface-2/60 px-4 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-text-3 first:border-t-0">{longDate(d, locale)}</div>
          <div className="divide-y divide-border">{ms.map((m) => <MatchCard key={m.id} m={m} state={liveState(m, now, feed[m.id])} teams={teams} />)}</div>
        </div>
      ))}
    </div>
  );
}
