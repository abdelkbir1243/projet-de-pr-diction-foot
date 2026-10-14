"use client";
/* Cartes d'analyse statistique d'un match : contexte, statistiques attendues, matchs comparables, modèle vs marché.
   Toutes lisent la prédiction produite par le pipeline (footpred/analyse.py) et n'inventent aucune donnée. */
import { Activity, CalendarRange, History, Info, Scale } from "lucide-react";
import type { Match, MatchContext, Prediction, TeamContext } from "@/lib/types";
import { cn, num, pct } from "@/lib/utils";
import { ProbabilityBar } from "../football";
import { Badge, Card, CardHeader } from "../ui/primitives";

/* ───────────── Contexte ───────────── */
function chips(c: TeamContext): { label: string; tone: "neutral" | "brand" | "warn" | "good" }[] {
  const out: { label: string; tone: "neutral" | "brand" | "warn" | "good" }[] = [];
  if (c.rank) out.push({ label: `${c.rank}e`, tone: "neutral" });
  if (c.champion) out.push({ label: "Champion en titre", tone: "brand" });
  if (c.firstSeason) out.push({ label: "Découvre la division", tone: "warn" });
  else if (c.promoted) out.push({ label: "Promu", tone: "warn" });
  if (c.titleRace) out.push({ label: "Course au titre", tone: "good" });
  if (c.europeRace) out.push({ label: "Course à l'Europe", tone: "good" });
  if (c.relegationFight) out.push({ label: "Lutte pour le maintien", tone: "warn" });
  if (c.nothingToPlayFor) out.push({ label: "Sans enjeu", tone: "neutral" });
  if (c.rest != null) out.push({ label: c.rest >= 14 ? "Repos ≥ 14 j" : `${c.rest} j de repos`, tone: c.rest <= 3 ? "warn" : "neutral" });
  return out;
}

export function ContextCard({ ctx, homeName, awayName }: { ctx: MatchContext; homeName: string; awayName: string }) {
  return (
    <Card>
      <CardHeader title="Contexte du match" subtitle="Classement de la veille, repos, statut et enjeu" icon={<CalendarRange className="size-4 text-brand" />}
        action={ctx.seasonStart ? <Badge tone="warn">Début de saison</Badge> : undefined} />
      <div className="grid gap-3 px-4 pb-3 sm:grid-cols-2">
        {([[homeName, ctx.home], [awayName, ctx.away]] as const).map(([n, c]) => (
          <div key={n} className="min-w-0 rounded-lg bg-surface-2 p-3">
            <div className="truncate text-[13px] font-semibold">{n}</div>
            <div className="mt-2 flex flex-wrap gap-1.5">{chips(c).map((x) => <Badge key={x.label} tone={x.tone}>{x.label}</Badge>)}</div>
          </div>
        ))}
      </div>
      {ctx.notes.length > 0 && (
        <ul className="space-y-1 border-t border-border px-4 py-3 text-[13px] text-text-2">
          {ctx.notes.map((t) => <li key={t} className="flex gap-2"><span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-brand" />{t}</li>)}
        </ul>
      )}
      <p className="border-t border-border px-4 py-2 text-[11px] leading-relaxed text-text-3">
        En fin de saison, le modèle v5 tient compte de l&apos;enjeu (titre, maintien, absence d&apos;objectif). Le repos, le statut de promu et le début de
        saison sont affichés pour information : testés sur 2021-2026, ils n&apos;améliorent pas significativement les prédictions.
      </p>
    </Card>
  );
}

/* ───────────── Statistiques attendues ───────────── */
function RangeTile({ label, mean, range, home, away, unit }: { label: string; mean: number; range: [number, number]; home: number; away: number; unit: string }) {
  return (
    <div className="min-w-0 rounded-xl border border-border bg-surface px-3.5 py-3">
      <div className="truncate text-[11px] font-medium uppercase tracking-wide text-text-3">{label}</div>
      <div className="tabular mt-1 text-xl font-semibold tracking-tight">{num(mean, 1)}</div>
      <div className="tabular mt-0.5 text-xs text-text-2">80 % des cas : {range[0]} à {range[1]} {unit}</div>
      <div className="tabular mt-2 flex justify-between text-[11px] text-text-3"><span className="text-home">{num(home, 1)}</span><span>dom. · ext.</span><span className="text-away">{num(away, 1)}</span></div>
    </div>
  );
}

export function ExpectedStatsCard({ p }: { p: Prediction }) {
  const e = p.expected;
  if (!e) return null;
  const dist = e.goals.dist;
  const max = Math.max(...dist, 0.01);
  return (
    <Card>
      <CardHeader title="Statistiques attendues" subtitle="Moyenne et intervalle où tombent 80 % des matchs simulés par le modèle" icon={<Activity className="size-4 text-brand" />} />
      <div className="snap-row -mx-0 px-4 pb-3 sm:grid sm:grid-cols-3 [&>*]:w-[70%] sm:[&>*]:w-auto">
        <RangeTile label="Buts" mean={e.goals.mean} range={e.goals.range} home={e.goals.home} away={e.goals.away} unit="buts" />
        {e.corners && <RangeTile label="Corners" mean={e.corners.mean} range={e.corners.range} home={e.corners.home} away={e.corners.away} unit="corners" />}
        {e.cards && <RangeTile label="Cartons jaunes" mean={e.cards.mean} range={e.cards.range} home={e.cards.home} away={e.cards.away} unit="cartons" />}
      </div>
      <div className="border-t border-border px-4 py-3">
        <div className="label-caps mb-2">Nombre total de buts</div>
        <div className="flex h-24 items-end gap-1.5" role="img" aria-label="Distribution du nombre total de buts">
          {dist.map((q, i) => (
            <div key={i} className="flex flex-1 flex-col items-center gap-1">
              <span className="tabular text-[10px] text-text-3">{Math.round(q * 100)}</span>
              <div className="bar-grow w-full rounded-t bg-brand/80" style={{ height: `${(q / max) * 60}px` }} title={`${i}${i === 6 ? "+" : ""} buts : ${pct(q, 1)}`} />
              <span className="tabular text-[11px] font-medium text-text-2">{i}{i === 6 ? "+" : ""}</span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

/* ───────────── Matchs comparables ───────────── */
export function SimilarMatchesCard({ p, homeName, awayName }: { p: Prediction; homeName: string; awayName: string }) {
  const s = p.similar;
  if (!s) return null;
  const rows: [string, string, string][] = [
    ["Buts / match", num(s.avgGoals, 2), num(p.xg.total, 2)], ["Plus de 2,5 buts", pct(s.over25), pct(p.over25)],
    ["Les deux marquent", pct(s.btts), pct(p.btts)], ["Corners / match", num(s.corners, 1), num(p.corners?.total, 1)], ["Cartons jaunes", num(s.cards, 1), num(p.cards?.total, 1)],
  ];
  return (
    <Card>
      <CardHeader title="Matchs comparables" subtitle={`Ce qui s'est réellement passé dans ${s.n} matchs semblables (10 dernières saisons)`} icon={<History className="size-4 text-brand" />} />
      <div className="px-4 pb-3">
        <ProbabilityBar home={s.homeWin} draw={s.draw} away={s.awayWin} labels={["Victoire domicile", "Nul", "Victoire extérieur"]} />
        <p className="mt-2 text-[11px] text-text-3">Écart d&apos;Elo entre {s.eloGap[0]} et {s.eloGap[1]} points en faveur de l&apos;équipe à domicile, niveau offensif proche de {homeName} – {awayName}.</p>
      </div>
      <table className="tabular w-full border-t border-border text-[13px]">
        <thead><tr className="text-[11px] uppercase tracking-wide text-text-3"><th className="py-2 pl-4 text-left font-medium">Indicateur</th><th className="font-medium">Observé</th><th className="pr-4 font-medium">Modèle</th></tr></thead>
        <tbody>{rows.map(([k, a, b]) => <tr key={k} className="border-t border-border/60 text-center"><td className="py-2 pl-4 text-left text-text-2">{k}</td><td className="font-semibold">{a}</td><td className="pr-4 text-text-2">{b}</td></tr>)}</tbody>
      </table>
    </Card>
  );
}

/* ───────────── Modèle vs marché ───────────── */
export function MarketCard({ m }: { m: Match }) {
  const mk = m.prediction?.market;
  if (!mk) {
    return (
      <Card>
        <CardHeader title="Modèle vs marché" icon={<Scale className="size-4 text-brand" />} />
        <p className="px-4 pb-4 text-[13px] text-text-2">Aucune cote d&apos;avant-match disponible pour ce match. Les cotes sont publiées par football-data.co.uk quelques jours avant la rencontre.</p>
      </Card>
    );
  }
  const tone = mk.agreement === "accord" ? "good" : mk.agreement === "désaccord modéré" ? "warn" : "live";
  return (
    <Card>
      <CardHeader title="Modèle vs marché" subtitle={`Probabilités implicites des cotes, marge de ${pct(mk.margin, 1)} retirée (méthode de Shin)`}
        icon={<Scale className="size-4 text-brand" />} action={<Badge tone={tone}>{mk.agreement}</Badge>} />
      <div className="space-y-3 px-4 pb-3">
        <div>
          <div className="label-caps mb-1">Modèle</div>
          <ProbabilityBar home={m.prediction!.home} draw={m.prediction!.draw} away={m.prediction!.away} variant="compact" />
        </div>
        <div>
          <div className="label-caps mb-1">Marché</div>
          <ProbabilityBar home={mk.home} draw={mk.draw} away={mk.away} variant="compact" />
        </div>
      </div>
      <div className="scrollbar-thin overflow-x-auto border-t border-border">
        <table className="tabular w-full min-w-[420px] text-[13px]">
          <thead><tr className="text-[11px] uppercase tracking-wide text-text-3">
            <th className="py-2 pl-4 text-left font-medium">Issue</th><th className="font-medium">Modèle</th><th className="font-medium">Marché</th>
            <th className="font-medium">Écart</th><th className="font-medium">Cote juste</th><th className="pr-4 font-medium">Cote</th>
          </tr></thead>
          <tbody>
            {mk.rows.map((r) => (
              <tr key={r.key} className="border-t border-border/60 text-center">
                <td className="py-2 pl-4 text-left font-medium">{r.key === "home" ? m.homeName : r.key === "away" ? m.awayName : r.key === "draw" ? "Nul" : "Plus de 2,5 buts"}</td>
                <td>{pct(r.model, 1)}</td><td>{pct(r.market, 1)}</td>
                <td className={cn("font-semibold", Math.abs(r.gap) < 0.03 ? "text-text-3" : r.gap > 0 ? "text-good" : "text-bad")}>{r.gap > 0 ? "+" : ""}{(100 * r.gap).toFixed(1)} pts</td>
                <td>{r.fairOdds.toFixed(2)}</td><td className="pr-4">{r.odds ? r.odds.toFixed(2) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="flex gap-1.5 border-t border-border px-4 py-2.5 text-[12px] leading-relaxed text-text-2">
        <Info className="mt-0.5 size-3.5 shrink-0 text-text-3" />
        <span>{mk.note} Sur 2015-2026, combiner le modèle et les cotes n&apos;améliore pas les cotes seules : un écart n&apos;est pas une opportunité, c&apos;est une question à étudier.</span>
      </p>
    </Card>
  );
}

/* ───────────── Provenance de la prédiction ───────────── */
export function PredictionSource({ p }: { p: Prediction }) {
  if (p.source === "frozen") return <Badge tone="good" title={p.frozenAt}>Figée avant le match</Badge>;
  if (p.source === "out-of-sample") return <Badge tone="outline" title="Match déjà joué, prédit par un modèle entraîné uniquement sur les saisons précédentes">Hors échantillon</Badge>;
  return <Badge tone="brand">Avant-match</Badge>;
}
