"use client";
/* Suivi jour par jour (hors échantillon) et fiabilité par degré de confiance. */
import { CalendarCheck, ShieldCheck } from "lucide-react";
import type { Performance, TrustLevel } from "@/lib/types";
import { cn, pct } from "@/lib/utils";
import { LineChart } from "./charts";
import { LevelChip } from "./confidence";
import { Card, CardHeader } from "./ui/primitives";

export function DailyTracking({ perf }: { perf: Performance }) {
  const days = perf.byDay ?? [];
  if (!days.length) return null;
  let cg = 0, cge = 0, cf = 0, cfe = 0;
  const data = days.map((d) => {
    cg += d.goals; cge += d.goalsExpected; cf += d.favWins; cfe += d.favExpected;
    return { x: new Date(d.date).toLocaleDateString("fr-FR", { day: "2-digit", month: "short" }), buts: cg, butsAtt: Math.round(cge * 10) / 10, fav: cf, favAtt: Math.round(cfe * 10) / 10 };
  });
  const last = [...days].reverse().slice(0, 10);
  const n = days.reduce((a, d) => a + d.n, 0);
  return (
    <Card>
      <CardHeader title="Suivi jour par jour" icon={<CalendarCheck className="size-4 text-brand" />}
        subtitle={`${days.length} dernières dates jouées · ${n} matchs · chaque saison prédite par un modèle entraîné sur les saisons précédentes`} />
      <div className="grid gap-4 px-3 pb-3 lg:grid-cols-2">
        <div><div className="label-caps px-1">Buts cumulés : attendus vs observés</div>
          <LineChart data={data} lines={[{ key: "butsAtt", name: "Attendus", color: "var(--draw)", dashed: true }, { key: "buts", name: "Observés", color: "var(--brand)" }]} height={220} /></div>
        <div><div className="label-caps px-1">Favoris gagnants cumulés : attendus vs observés</div>
          <LineChart data={data} lines={[{ key: "favAtt", name: "Attendus", color: "var(--draw)", dashed: true }, { key: "fav", name: "Observés", color: "var(--home)" }]} height={220} /></div>
      </div>
      <div className="scrollbar-thin overflow-x-auto border-t border-border">
        <table className="tabular w-full min-w-[560px] text-[13px]">
          <thead><tr className="text-[11px] uppercase tracking-wide text-text-3">
            <th className="py-2 pl-4 text-left font-medium">Date</th><th className="font-medium">Matchs</th><th className="font-medium">Buts (att.)</th>
            <th className="font-medium">Favoris (att.)</th><th className="font-medium">Nuls (att.)</th><th className="font-medium">+2,5 (att.)</th><th className="pr-4 font-medium">Log loss</th>
          </tr></thead>
          <tbody>{last.map((d) => (
            <tr key={d.date} className="border-t border-border/60 text-center">
              <td className="py-2 pl-4 text-left">{new Date(d.date).toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" })}</td>
              <td>{d.n}</td><td>{d.goals} <span className="text-text-3">({d.goalsExpected.toFixed(1)})</span></td>
              <td>{d.favWins} <span className="text-text-3">({d.favExpected.toFixed(1)})</span></td><td>{d.draws} <span className="text-text-3">({d.drawExpected.toFixed(1)})</span></td>
              <td>{d.over25} <span className="text-text-3">({d.over25Expected.toFixed(1)})</span></td>
              <td className={cn("pr-4", d.logLoss > 1.07 ? "text-bad" : d.logLoss < 0.95 ? "text-good" : "")}>{d.logLoss.toFixed(3)}</td>
            </tr>))}</tbody>
        </table>
      </div>
      <p className="border-t border-border px-4 py-2 text-[11px] text-text-3">Un jour isolé varie beaucoup (quelques matchs) : c&apos;est la proximité des courbes cumulées qui montre si le modèle est bien calibré. Log loss : 1,07 = aucune information.</p>
    </Card>
  );
}

export function ConfidenceLevels({ perf }: { perf: Performance }) {
  const c = perf.confidence;
  if (!c) return null;
  return (
    <Card>
      <CardHeader title="Fiabilité par degré de confiance" icon={<ShieldCheck className="size-4 text-brand" />}
        subtitle={`Réussite du favori du modèle, ${perf.backtest ? `${perf.backtest.matches.toLocaleString("fr-FR")} matchs ${perf.backtest.seasons[0]}-${perf.backtest.seasons[1]}` : "hors échantillon"}`} />
      <div className="grid gap-3 px-4 pb-4 sm:grid-cols-3">
        {(["A", "B", "C"] as TrustLevel[]).filter((k) => c.levels[k]).map((k) => {
          const l = c.levels[k];
          return (
            <div key={k} className="rounded-xl border border-border p-3.5">
              <div className="flex items-center justify-between"><LevelChip level={k} long /><span className="tabular text-[11px] text-text-3">{pct(l.share)} des matchs</span></div>
              <div className="tabular mt-2 text-[13px]">Annoncé <b>{pct(l.announced, 1)}</b> · réalisé <b>{pct(l.observed, 1)}</b></div>
              <div className="tabular text-[11px] text-text-3">IC 95 % {pct(l.lo, 1)} – {pct(l.hi, 1)} · {l.n.toLocaleString("fr-FR")} matchs · log loss {l.logLoss.toFixed(3)}</div>
            </div>
          );
        })}
      </div>
      {perf.families && (
        <div className="border-t border-border px-4 py-3">
          <div className="label-caps mb-2">Calibration par famille de statistiques (écart moyen annoncé / réalisé)</div>
          <div className="flex flex-wrap gap-2">
            {perf.families.map((f) => (
              <span key={f.family} className="tabular rounded-lg bg-surface-2 px-2.5 py-1.5 text-[12px]"><b className="font-medium">{f.family}</b> · {(f.ece * 100).toFixed(1)} pt · {f.n.toLocaleString("fr-FR")} cas</span>
            ))}
          </div>
        </div>
      )}
      <p className="border-t border-border px-4 py-2 text-[11px] leading-relaxed text-text-3">
        A : accord avec les cotes et saison installée. B : désaccord modéré ou moins de 4 matchs joués. C : désaccord marqué (≥ 10 points) — le modèle y est trop confiant.
      </p>
    </Card>
  );
}

export function CupPerformance({ perf }: { perf: Performance }) {
  const c = perf.cups;
  if (!c) return null;
  const NOMS: Record<string, string> = { CL: "Ligue des champions", EL: "Ligue Europa", ECL: "Conference League" };
  const skill = 1 - c.logLoss / c.baseline;
  return (
    <Card>
      <CardHeader title="Coupes d'Europe · modèle Elo" icon={<ShieldCheck className="size-4 text-brand" />}
        subtitle={`${c.matches.toLocaleString("fr-FR")} matchs prédits hors échantillon (chaque saison par un modèle entraîné sur les précédentes)`} />
      <div className="tabular grid gap-3 px-4 pb-4 sm:grid-cols-4">
        <div className="rounded-xl border border-border p-3"><div className="label-caps">Bon résultat</div><div className="text-xl font-semibold">{pct(c.accuracy, 1)}</div></div>
        <div className="rounded-xl border border-border p-3"><div className="label-caps">Log loss</div><div className="text-xl font-semibold">{c.logLoss.toFixed(3)}</div><div className="text-[11px] text-text-3">fréquences seules {c.baseline.toFixed(3)}</div></div>
        <div className="rounded-xl border border-border p-3"><div className="label-caps">Skill score</div><div className="text-xl font-semibold">{pct(skill, 1)}</div></div>
        <div className="rounded-xl border border-border p-3"><div className="label-caps">Calibration (ECE)</div><div className="text-xl font-semibold">{c.ece.toFixed(3)}</div></div>
      </div>
      <div className="flex flex-wrap gap-2 border-t border-border px-4 py-3">
        {Object.entries(c.byCup).map(([k, v]) => (
          <span key={k} className="tabular rounded-lg bg-surface-2 px-2.5 py-1.5 text-[12px]"><b className="font-medium">{NOMS[k] ?? k}</b> · {pct(v.accuracy, 1)} · log loss {v.logLoss.toFixed(3)} · {v.n} matchs</span>
        ))}
      </div>
      <p className="border-t border-border px-4 py-2 text-[11px] leading-relaxed text-text-3">
        Pas de cotes gratuites pour les coupes : pas de comparaison avec le marché. Les clubs hors des championnats suivis ont un Elo estimé sur leurs seuls matchs européens (niveau de confiance C quand les deux le sont).
      </p>
    </Card>
  );
}
