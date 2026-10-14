"use client";
/* Analyse de la journée : ce que le modèle attend de l'ensemble des matchs d'une date (intervalles à 80 %),
   les statistiques les mieux étayées par l'historique, puis le bilan attendu / observé une fois les matchs joués. */
import Link from "next/link";
import { CalendarDays, Check, ChevronDown, X } from "lucide-react";
import type { DaySummary, Range } from "@/lib/types";
import { cn, pct } from "@/lib/utils";
import { LevelChip } from "./confidence";
import { Card } from "./ui/primitives";

function Tile({ label, r, actual, unit }: { label: string; r: Range; actual?: number | null; unit?: string }) {
  const inside = actual != null && actual >= r.range[0] && actual <= r.range[1];
  return (
    <div className="min-w-0 rounded-xl border border-border bg-surface px-3 py-2.5">
      <div className="truncate text-[11px] font-medium uppercase tracking-wide text-text-3">{label}</div>
      <div className="tabular mt-0.5 text-lg font-semibold">{r.expected.toLocaleString("fr-FR", { maximumFractionDigits: 1 })}{unit && <span className="ml-0.5 text-[12px] font-normal text-text-3">{unit}</span>}</div>
      <div className="tabular text-[11px] text-text-2">80 % : {r.range[0]} à {r.range[1]}</div>
      {actual != null && (
        <div className={cn("tabular mt-1 inline-flex items-center gap-1 rounded px-1.5 py-px text-[11px] font-semibold", inside ? "bg-good-soft text-good" : "bg-warn-soft text-warn")}>
          {inside ? <Check className="size-3" /> : <X className="size-3" />}réalisé {actual}
        </div>
      )}
    </div>
  );
}

export function DaySummaryCard({ day, label }: { day: DaySummary; label: string }) {
  const r = day.result;
  const complete = r && r.n === day.n;
  return (
    <Card className="relative overflow-hidden">
      <span className="ai-gradient absolute inset-x-0 top-0 h-0.5" aria-hidden />
      <details className="group" open>
        <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-3 gap-y-1.5 px-4 pb-2 pt-3.5">
          <CalendarDays className="size-4 text-brand" />
          <span className="text-[12px] font-semibold uppercase tracking-[0.06em] text-text-2">Analyse de la journée · {label}</span>
          <span className="flex items-center gap-1">
            {(["A", "B", "C"] as const).filter((k) => day.levels[k]).map((k) => <span key={k} className="flex items-center gap-0.5"><LevelChip level={k} /><span className="tabular text-[11px] text-text-3">×{day.levels[k]}</span></span>)}
          </span>
          <ChevronDown className="ml-auto size-4 text-text-3 transition-transform group-open:rotate-180" />
        </summary>
        <p className="px-4 text-[12px] text-text-3">
          {day.n} match{day.n > 1 ? "s" : ""} analysé{day.n > 1 ? "s" : ""}{r ? ` · ${r.n} joué${r.n > 1 ? "s" : ""}` : ""}. Les intervalles contiennent le résultat de la journée dans 80 % des cas si le modèle est bien calibré.
        </p>
        <div className="snap-row mt-3 px-4 sm:grid sm:grid-cols-3 lg:grid-cols-6 [&>*]:w-[42%] sm:[&>*]:w-auto">
          <Tile label="Buts" r={day.goals} actual={complete ? r!.goals : null} />
          <Tile label="Victoires dom." r={day.homeWins} actual={complete ? r!.homeWins : null} />
          <Tile label="Nuls" r={day.draws} actual={complete ? r!.draws : null} />
          <Tile label="Victoires ext." r={day.awayWins} actual={complete ? r!.awayWins : null} />
          <Tile label="Matchs +2,5 buts" r={day.over25} actual={complete ? r!.over25 : null} />
          <Tile label="Favoris gagnants" r={day.favWins} actual={complete ? r!.favWins : null} />
        </div>
        <div className="grid gap-3 px-4 py-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
          <div className="space-y-2 text-[13px]">
            <Link href={`/match/${day.clearest.match}`} className="block rounded-lg bg-surface-2 px-3 py-2 transition-colors hover:text-brand">
              <span className="label-caps block">Favori le plus net</span>{day.clearest.label} <span className="tabular text-text-3">· {pct(day.clearest.p)}</span>
            </Link>
            <Link href={`/match/${day.mostOpen.match}`} className="block rounded-lg bg-surface-2 px-3 py-2 transition-colors hover:text-brand">
              <span className="label-caps block">Match le plus ouvert</span>{day.mostOpen.label} <span className="tabular text-text-3">· favori à {pct(day.mostOpen.p)}</span>
            </Link>
            {day.corners && <div className="rounded-lg bg-surface-2 px-3 py-2"><span className="label-caps block">Corners de la journée</span><span className="tabular">{day.corners.expected} attendus (80 % : {day.corners.range[0]}–{day.corners.range[1]})</span></div>}
            {r && <div className="rounded-lg bg-surface-2 px-3 py-2"><span className="label-caps block">Bilan des matchs joués</span><span className="tabular">{r.goals} buts pour {r.goalsExpected} attendus · favoris {r.favWins}/{r.n} pour {r.favExpected} attendus</span></div>}
          </div>
          {day.best.length > 0 && (
            <div>
              <div className="label-caps mb-1.5">Statistiques les mieux étayées par l&apos;historique</div>
              <ul className="divide-y divide-border rounded-lg border border-border">
                {day.best.map((b) => (
                  <li key={b.match + b.market}>
                    <Link href={`/match/${b.match}?tab=prediction`} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 px-3 py-2 text-[13px] transition-colors hover:bg-surface-2">
                      <span className="min-w-0"><span className="block truncate font-medium">{b.market}</span><span className="block truncate text-[11px] text-text-3">{b.homeName} – {b.awayName}</span></span>
                      <span className="tabular font-semibold">{pct(b.p)}</span>
                      <span className="tabular col-span-2 text-[11px] text-text-3">historiquement réalisé {pct(b.observed)} [{Math.round(b.lo * 100)}–{Math.round(b.hi * 100)}] sur {b.n.toLocaleString("fr-FR")} cas</span>
                    </Link>
                  </li>
                ))}
              </ul>
              <p className="mt-1.5 text-[11px] text-text-3">Probabilité du modèle, puis fréquence réellement observée quand il annonçait une valeur proche. Une statistique probable n&apos;est pas un conseil de pari.</p>
            </div>
          )}
        </div>
      </details>
    </Card>
  );
}
