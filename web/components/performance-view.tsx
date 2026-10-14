"use client";
import { useMemo, useState } from "react";
import { CheckCircle2, CircleX, Info, Radio } from "lucide-react";
import type { Performance, TeamLite } from "@/lib/types";
import { cn, pct, tierColor } from "@/lib/utils";
import { CalibrationChart, LineChart } from "./charts";
import { PredictionHistory } from "./prediction-history";
import { ConfidenceLevels, CupPerformance, DailyTracking } from "./daily-tracking";
import { Card, CardHeader, Stat } from "./ui/primitives";

export function PerformanceView({ perf, teams }: { perf: Performance; teams: Record<string, TeamLite> }) {
  const [filter, setFilter] = useState<"all" | "ok" | "ko">("all");
  const [page, setPage] = useState(0);
  const per = 25;
  const hist = useMemo(() => perf.history.filter((h) => filter === "all" || (filter === "ok" ? h.correct : !h.correct)), [perf.history, filter]);
  const months = perf.byMonth.filter((m) => m.n >= 20).map((m) => ({
    x: new Date(m.month + "-01").toLocaleDateString("fr-FR", { month: "short", year: "2-digit" }),
    modele: m.logLoss, cotes: m.marketLogLoss, acc: m.accuracy,
  }));
  const skill = 1 - perf.logLoss / perf.baseline.logLoss, mskill = 1 - perf.market.logLoss / perf.baseline.logLoss;
  return (
    <div className="space-y-4">
      <div className="snap-row -mx-3 px-3 sm:mx-0 sm:grid sm:grid-cols-3 sm:px-0 xl:grid-cols-6 [&>*]:w-[46%] sm:[&>*]:w-auto">
        <Stat label="Total Predictions" value={perf.matches.toLocaleString("fr-FR")} sub="hors échantillon" />
        <Stat label="Accuracy" value={pct(perf.accuracy, 1)} bar={perf.accuracy} sub={`cotes ${pct(perf.market.accuracy, 1)} · base ${pct(perf.baseline.accuracy, 1)}`} />
        <Stat label="Brier score" value={perf.brier.toFixed(3)} sub={`cotes ${perf.market.brier.toFixed(3)} · plus bas = mieux`} />
        <Stat label="Log loss" value={perf.logLoss.toFixed(3)} sub={`cotes ${perf.market.logLoss.toFixed(3)} · sans info ${perf.baseline.logLoss.toFixed(3)}`} />
        <Stat label="Calibration (ECE)" value={perf.ece.toFixed(3)} bar={1 - Math.min(1, perf.ece * 10)} sub="0 = parfaitement calibré" />
        <Stat label="RPS" value={perf.rps.toFixed(3)} sub="ordre 1 < X < 2" />
      </div>
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <div className="min-w-[240px] flex-1">
            <div className="mb-1.5 flex justify-between text-[13px]"><span className="font-medium">Information captée par le modèle</span><span className="tabular text-text-2">{pct(skill / mskill)} de celle des cotes</span></div>
            <div className="relative h-3 rounded-full bg-surface-3">
              <div className="ai-gradient bar-grow absolute inset-y-0 left-0 rounded-full" style={{ width: `${(skill / mskill) * 100}%` }} />
              <div className="absolute inset-y-[-3px] right-0 w-0.5 rounded bg-text-3" title="Cotes du marché" />
            </div>
            <div className="mt-1 flex justify-between text-[11px] text-text-3"><span>Aucune information (fréquences)</span><span>Cotes des bookmakers</span></div>
          </div>
          <p className="max-w-md text-xs leading-relaxed text-text-2">
            Skill score {pct(skill, 1)} contre {pct(mskill, 1)} pour les cotes. Le marché intègre des informations absentes de nos données (compositions, blessures) : le modèle ne le bat pas, et nous l'affichons.
          </p>
        </div>
      </Card>
      <DailyTracking perf={perf} />
      <ConfidenceLevels perf={perf} />
      <CupPerformance perf={perf} />
      {perf.live && (
        <Card className="flex flex-wrap items-center gap-4 border-brand/40 p-4">
          <span className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-brand-ink"><Radio className="size-4" />Suivi en conditions réelles</span>
          <span className="tabular text-[13px] text-text-2">{perf.live.n} prédictions figées avant le coup d'envoi · accuracy {pct(perf.live.accuracy, 1)} · log loss {perf.live.logLoss.toFixed(3)} · Brier {perf.live.brier.toFixed(3)}</span>
        </Card>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Probabilité annoncée vs résultats réels" subtitle="Calibration : chaque point regroupe ~10 % des prédictions (1, X et 2)" />
          <div className="p-3"><CalibrationChart points={perf.calibration} /></div>
          <p className="flex gap-1.5 border-t border-border px-4 py-2 text-[11px] text-text-3"><Info className="mt-0.5 size-3.5 shrink-0" />Sur la diagonale, une issue annoncée à 40 % se produit 40 % du temps.</p>
        </Card>
        <Card>
          <CardHeader title="Évolution dans le temps" subtitle="Log loss mensuelle (plus bas = mieux) · modèle vs cotes" />
          <div className="p-3"><LineChart data={months} lines={[{ key: "modele", name: "Modèle", color: "var(--home)" }, { key: "cotes", name: "Cotes", color: "var(--draw)", dashed: true }]} yFormat={(v) => v.toFixed(2)} height={280} /></div>
        </Card>
        <Card>
          <CardHeader title="Accuracy mensuelle" subtitle="Part des matchs où l'issue la plus probable s'est réalisée" />
          <div className="p-3"><LineChart data={months} lines={[{ key: "acc", name: "Accuracy", color: "var(--brand)" }]} yFormat={(v) => `${Math.round(v * 100)} %`} yDomain={[0.3, 0.7]} height={240} /></div>
        </Card>
        {perf.tiers && (
          <Card>
            <CardHeader title="Fiabilité des paliers de risque" subtitle="30 marchés × tous les matchs 2021-2026, probabilité annoncée vs réalisée" />
            <div className="scrollbar-thin overflow-x-auto"><table className="tabular w-full min-w-[420px] text-[13px]">
              <thead><tr className="border-b border-border text-[11px] uppercase tracking-wide text-text-3"><th className="py-2 pl-4 text-left font-medium">Palier</th><th className="font-medium">Décisions</th><th className="font-medium">Annoncé</th><th className="font-medium">Réalisé</th><th className="pr-4 font-medium">Rendement aux cotes</th></tr></thead>
              <tbody>{perf.tiers.map((t) => (
                <tr key={t.tier} className="border-b border-border text-center last:border-0">
                  <td className="py-2 pl-4 text-left"><span className={cn("rounded px-1.5 py-0.5 text-[11px] font-semibold", tierColor(t.tier))}>{t.tier.slice(4)}</span></td>
                  <td className="text-text-2">{t.decisions.toLocaleString("fr-FR")}</td><td>{pct(t.predicted, 1)}</td><td className="font-semibold">{pct(t.observed, 1)}</td>
                  <td className={cn("pr-4", t.returnAtOdds < 0 ? "text-bad" : "text-good")}>{(t.returnAtOdds * 100).toFixed(1)} %</td>
                </tr>))}</tbody>
            </table></div>
            <p className="border-t border-border px-4 py-2 text-[11px] text-text-3">Le classement par risque est fiable, mais aucun palier n'est rentable aux cotes réelles : moins de risque ne veut pas dire meilleure décision.</p>
          </Card>
        )}
      </div>
      <Card>
        <CardHeader title="Prediction History" subtitle={perf.scope} />
        <div className="-mt-1 flex gap-1 px-4 pb-3 text-xs">
              {([["all", "Toutes"], ["ok", "Réussies"], ["ko", "Manquées"]] as const).map(([v, l]) => (
                <button key={v} onClick={() => { setFilter(v); setPage(0); }} className={cn("inline-flex items-center gap-1 rounded-md px-2 py-1 font-medium", filter === v ? "bg-brand-soft text-brand-ink" : "text-text-2 hover:bg-surface-2")}>
                  {v === "ok" && <CheckCircle2 className="size-3.5" />}{v === "ko" && <CircleX className="size-3.5" />}{l}
                </button>
              ))}
        </div>
        <PredictionHistory rows={hist.slice(page * per, page * per + per)} teams={teams} />
        <div className="flex items-center justify-between border-t border-border px-4 py-2 text-xs text-text-2">
          <span className="tabular">{hist.length ? `${page * per + 1}–${Math.min(hist.length, page * per + per)} sur ${hist.length}` : "0"}</span>
          <div className="flex gap-1">
            <button disabled={page === 0} onClick={() => setPage(page - 1)} className="rounded-md border border-border px-2 py-1 disabled:opacity-40">Précédent</button>
            <button disabled={(page + 1) * per >= hist.length} onClick={() => setPage(page + 1)} className="rounded-md border border-border px-2 py-1 disabled:opacity-40">Suivant</button>
          </div>
        </div>
      </Card>
    </div>
  );
}
