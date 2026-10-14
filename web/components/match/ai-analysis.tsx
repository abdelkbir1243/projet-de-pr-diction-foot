"use client";
import { CalibLine } from "../confidence";
/* AI ANALYSIS : probabilités de victoire, indicateurs clés, ratings, radar, facteurs explicatifs, scores, corners/cartons, marchés. */
import { BrainCircuit, ChevronDown, Info, Lightbulb, ShieldCheck, Target } from "lucide-react";
import type { Match, Team, TeamLite } from "@/lib/types";
import { useI18n } from "@/lib/i18n";
import { keyFactors, radarAxes, ratings, uncertaintyLabel } from "@/lib/insights";
import { cn, fairOdds, pct, tierColor } from "@/lib/utils";
import { Donut, RadarCompare } from "../charts";
import { ProbabilityBar, TeamLogo } from "../football";
import { Badge, Card, CardHeader, EmptyState, Stat } from "../ui/primitives";

export function AIAnalysis({ m, home, away, teams }: { m: Match; home: Team | null; away: Team | null; teams: Record<string, TeamLite> }) {
  const { t } = useI18n();
  const p = m.prediction;
  if (!p) return <Card><EmptyState icon={<BrainCircuit className="size-5" />} title={t("match.noPrediction")} hint="Le modèle couvre les 5 grands championnats et les coupes d'Europe. Aucune prédiction n'est publiée après le coup d'envoi." /></Card>;
  const h = m.home ? teams[m.home] : null, a = m.away ? teams[m.away] : null;
  const unc = uncertaintyLabel(p);
  // coupes : les percentiles et facteurs propres à un championnat ne sont pas comparables entre deux ligues
  const cup = p.scope === "cup";
  const factors = home && away && !cup ? keyFactors(home, away, p) : [];
  return (
    <div className="space-y-4">
      {/* ── Win probability ── */}
      <Card className="relative overflow-hidden">
        <span className="ai-gradient absolute inset-x-0 top-0 h-1" aria-hidden />
        <div className="flex flex-wrap items-center justify-between gap-2 px-4 pt-4 sm:px-5">
          <div className="flex items-center gap-2"><span className="ai-gradient grid size-7 place-items-center rounded-lg text-white"><BrainCircuit className="size-4" /></span>
            <h2 className="text-[13px] font-bold uppercase tracking-[0.14em] ai-text">AI Analysis</h2></div>
          <div className="flex items-center gap-1.5"><Badge tone={unc.tone}>{unc.label}</Badge><Badge tone="outline">Modèle {p.model}{p.frozenAt ? " · figé avant le match" : ""}</Badge></div>
        </div>
        <div className="grid gap-6 p-4 sm:p-5 md:grid-cols-[1fr_220px] md:items-center">
          <div>
            <div className="label-caps mb-3">Win probability</div>
            <ProbabilityBar home={p.home} draw={p.draw} away={p.away} labels={[m.homeName, t("match.draw"), m.awayName]} />
            <div className="tabular mt-4 grid grid-cols-3 gap-2 text-center text-[11px] text-text-3">
              <span>cote juste {fairOdds(p.home)}</span><span>cote juste {fairOdds(p.draw)}</span><span>cote juste {fairOdds(p.away)}</span>
            </div>
          </div>
          <div className="flex items-center gap-4 md:flex-col md:gap-2">
            <div className="w-[140px] shrink-0"><Donut height={140} values={[{ name: "Confiance", value: p.confidence, color: "var(--brand)" }, { name: "", value: 1 - p.confidence, color: "var(--surface-3)" }]}
              center={<div><div className="tabular text-2xl font-semibold">{pct(p.confidence)}</div><div className="text-[10px] uppercase tracking-wide text-text-3">Confidence</div></div>} /></div>
            <p className="max-w-[220px] text-[11px] leading-relaxed text-text-3 md:text-center">
              {p.trust?.evidence ? <>Degré de confiance {p.trust.label.toLowerCase()} : dans {p.trust.evidence.n.toLocaleString("fr-FR")} matchs comparables, le favori a gagné {pct(p.trust.evidence.observed)} du temps.</>
                : <>À ce niveau de netteté, l&apos;issue favorite s&apos;est réalisée {pct(p.confidence)} du temps (5 dernières saisons, hors échantillon).</>}
            </p>
          </div>
        </div>
      </Card>

      {/* ── Indicateurs clés ── */}
      <div className="snap-row lg:grid lg:grid-cols-6 lg:overflow-visible">
        <Stat className="min-w-[132px]" label="Predicted score" value={`${p.likelyScore.home} – ${p.likelyScore.away}`} sub={`${pct(p.likelyScore.p, 1)} de probabilité`} />
        <Stat className="min-w-[132px]" label="Expected goals" value={p.xg.total.toFixed(2)} sub={`${p.xg.home.toFixed(2)} – ${p.xg.away.toFixed(2)}`} />
        <Stat className="min-w-[132px]" label="Over 2,5" value={pct(p.over25)} bar={p.over25} />
        <Stat className="min-w-[132px]" label="BTTS" value={pct(p.btts)} bar={p.btts} />
        <Stat className="min-w-[132px]" label={`Clean sheet ${h?.code ?? ""}`} value={pct(p.cleanSheetHome)} bar={p.cleanSheetHome} tone="home" />
        <Stat className="min-w-[132px]" label={`Clean sheet ${a?.code ?? ""}`} value={pct(p.cleanSheetAway)} bar={p.cleanSheetAway} tone="away" />
      </div>

      {home && away && !cup && (
        <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
          {/* ── Ratings ── */}
          <Card>
            <CardHeader title="Ratings" subtitle="Percentiles 0-100 au sein du championnat" />
            <div className="space-y-3 px-4 pb-4">
              {ratings(home, away).map((r) => (
                <div key={r.key}>
                  <div className="mb-1 flex items-baseline justify-between text-[13px]"><span className="font-medium">{r.label}</span><span className="text-[11px] text-text-3">{r.hint}</span></div>
                  <div className="grid grid-cols-[28px_1fr_28px] items-center gap-2">
                    <span className="tabular text-right text-[13px] font-semibold text-home">{r.home}</span>
                    <div className="flex h-2 gap-1">
                      <div className="flex flex-1 justify-end rounded-full bg-surface-3"><div className="bar-grow-r h-full rounded-full bg-home" style={{ width: `${r.home}%` }} /></div>
                      <div className="flex-1 rounded-full bg-surface-3"><div className="bar-grow h-full rounded-full bg-away" style={{ width: `${r.away}%` }} /></div>
                    </div>
                    <span className="tabular text-[13px] font-semibold text-away">{r.away}</span>
                  </div>
                </div>
              ))}
              <div className="flex justify-between pt-1 text-[11px] text-text-3"><span className="flex items-center gap-1"><TeamLogo team={h} size={14} />{m.homeName}</span><span className="flex items-center gap-1">{m.awayName}<TeamLogo team={a} size={14} /></span></div>
            </div>
          </Card>
          {/* ── Radar ── */}
          <Card>
            <CardHeader title="Profil comparé" subtitle="Attack · Defense · Form · Possession · Finishing · Consistency" />
            <div className="px-2 pb-2"><RadarCompare data={radarAxes(home, away)} homeName={m.homeName} awayName={m.awayName} height={290} /></div>
          </Card>
        </div>
      )}

      {/* ── AI Match Insight ── */}
      <Card>
        <CardHeader title="AI Match Insight" icon={<Lightbulb className="size-4 text-brand" />} subtitle="Ce qui explique les probabilités" />
        <div className="grid gap-4 px-4 pb-4 md:grid-cols-[1fr_1fr]">
          <p className="text-[15px] leading-relaxed text-text">{p.synthesis}</p>
          {factors.length > 0 && (
            <ul className="space-y-2.5">
              {factors.map((f) => (
                <li key={f.label}>
                  <div className="flex items-baseline justify-between gap-2 text-[13px]"><span className="font-medium">{f.label}</span><span className="truncate text-xs text-text-3">{f.detail}</span></div>
                  <div className="mt-1 h-1.5 rounded-full bg-surface-3">
                    <div className={cn("bar-grow h-full rounded-full", f.side === "home" ? "bg-home" : f.side === "away" ? "bg-away" : "bg-draw")} style={{ width: `${Math.max(12, f.weight * 100)}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
        <p className="flex gap-1.5 border-t border-border px-4 py-2 text-[11px] text-text-3"><Info className="mt-0.5 size-3.5 shrink-0" />{p.scope === "cup" ? "Modèle coupes d'Europe : Elo (ClubElo ou estimé), logit 1X2 et Poisson–Dixon-Coles. Probabilités, jamais des résultats garantis." : "Probabilités statistiques issues d'un modèle (Elo, pi-ratings, GAS, Poisson–Dixon-Coles), jamais des résultats garantis."}</p>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Scores les plus probables" subtitle="Poisson + correction Dixon-Coles" icon={<Target className="size-4 text-text-3" />} />
          <ul className="space-y-2 px-4 pb-4">
            {p.topScores.map((s, i) => (
              <li key={s.score} className="grid grid-cols-[56px_1fr_48px] items-center gap-3 text-[13px]">
                <span className="tabular font-semibold">{s.score.replace("-", " – ")}</span>
                <div className="h-2 rounded-full bg-surface-3"><div className={cn("bar-grow h-full rounded-full", i === 0 ? "ai-gradient" : "bg-brand/50")} style={{ width: `${(s.p / p.topScores[0].p) * 100}%` }} /></div>
                <span className="tabular text-right text-text-2">{pct(s.p, 1)}</span>
              </li>
            ))}
          </ul>
          <div className="tabular grid grid-cols-3 gap-2 border-t border-border px-4 py-3 text-center">
            {[["+1,5 buts", p.over15], ["+3,5 buts", p.over35], ["But 1re MT", p.firstHalfGoal]].map(([k, v]) => (
              <div key={k as string}><div className="text-[10px] uppercase tracking-wide text-text-3">{k}</div><div className="text-[15px] font-semibold">{pct(v as number)}</div></div>
            ))}
          </div>
        </Card>
        {p.corners && p.cards ? (() => { const co = p.corners!, ca = p.cards!; return (
        <Card>
          <CardHeader title="Corners & cartons" subtitle="Modèles de comptage (binomiale négative)" icon={<ShieldCheck className="size-4 text-text-3" />} />
          <div className="tabular grid grid-cols-3 gap-2 px-4 text-center">
            <div className="rounded-lg bg-surface-2 py-2"><div className="text-[10px] uppercase tracking-wide text-text-3">Corners</div><div className="text-lg font-semibold">{co.total.toFixed(1)}</div><div className="text-[11px] text-text-3">{co.home.toFixed(1)} – {co.away.toFixed(1)}</div></div>
            <div className="rounded-lg bg-surface-2 py-2"><div className="text-[10px] uppercase tracking-wide text-text-3">Jaunes</div><div className="text-lg font-semibold">{ca.total.toFixed(1)}</div><div className="text-[11px] text-text-3">{ca.home.toFixed(1)} – {ca.away.toFixed(1)}</div></div>
            <div className="rounded-lg bg-surface-2 py-2"><div className="text-[10px] uppercase tracking-wide text-text-3">≥ 1 rouge</div><div className="text-lg font-semibold">{pct(ca.red)}</div></div>
          </div>
          <div className="space-y-2 px-4 py-3">
            {[...Object.entries(co.over).slice(1, 4).map(([k, v]) => [`Plus de ${k.replace(".", ",")} corners`, v] as const),
              ...Object.entries(ca.over).slice(1, 3).map(([k, v]) => [`Plus de ${k.replace(".", ",")} jaunes`, v] as const)].map(([k, v]) => (
              <div key={k} className="grid grid-cols-[1fr_80px_40px] items-center gap-2 text-[13px]">
                <span className="text-text-2">{k}</span><div className="h-1.5 rounded-full bg-surface-3"><div className="bar-grow h-full rounded-full bg-brand/60" style={{ width: `${v * 100}%` }} /></div><span className="tabular text-right font-semibold">{pct(v)}</span>
              </div>
            ))}
          </div>
        </Card>); })() : (
          <Card>
            <CardHeader title="Niveau Elo" subtitle="Modèle coupes d'Europe : l'Elo est la seule variable comparable entre championnats" icon={<ShieldCheck className="size-4 text-text-3" />} />
            {p.elo ? (
              <div className="tabular grid grid-cols-2 gap-2 px-4 pb-4 text-center">
                {([[m.homeName, p.elo.home, p.elo.homeEstimated], [m.awayName, p.elo.away, p.elo.awayEstimated]] as const).map(([n, e, est]) => (
                  <div key={n} className="rounded-lg bg-surface-2 py-3"><div className="truncate px-2 text-[11px] uppercase tracking-wide text-text-3">{n}</div>
                    <div className="text-2xl font-semibold">{e}</div><div className="text-[11px] text-text-3">{est ? "estimé (matchs européens)" : "ClubElo"}</div></div>
                ))}
                <p className="col-span-2 text-left text-[11px] leading-relaxed text-text-3">100 points d&apos;écart ≈ 64 % de chances de victoire hors avantage du terrain. Pas de corners ni de cartons pour les coupes : ces statistiques ne sont pas disponibles gratuitement.</p>
              </div>
            ) : <p className="px-4 pb-4 text-[13px] text-text-3">Corners et cartons non modélisés pour cette compétition.</p>}
          </Card>
        )}
      </div>

      {/* ── Lecture du risque + tous les marchés (repliable) ── */}
      <Card>
        <CardHeader title="Lecture du risque" subtitle="Trois issues de référence, du moins au plus risqué" />
        <div className="grid gap-2 px-4 pb-4 sm:grid-cols-3">
          {p.decisions.map((d) => (
            <div key={d.profile} className="rounded-lg border border-border p-3">
              <div className="flex items-center justify-between"><span className="text-[11px] font-semibold uppercase tracking-wide text-text-3">{d.profile}</span><span className={cn("rounded px-1.5 py-0.5 text-[10px] font-semibold", tierColor(d.tier))}>{d.tier.slice(4)}</span></div>
              <div className="mt-1.5 text-[13px] font-medium">{d.market}</div>
              <div className="tabular mt-1 text-lg font-semibold">{pct(d.p)}</div>
            </div>
          ))}
        </div>
        {p.markets.length > 0 && (
          <details className="group border-t border-border">
            <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-[13px] font-medium text-text-2 hover:text-text">
              Tous les marchés ({p.markets.length}) · avec leur fréquence réalisée historiquement <ChevronDown className="size-4 transition-transform group-open:rotate-180" />
            </summary>
            <ul className="divide-y divide-border border-t border-border">
              {p.markets.map((x) => (
                <li key={x.market} className="grid grid-cols-[1fr_auto] items-center gap-2 px-4 py-2 text-[13px] sm:grid-cols-[1fr_120px_140px_56px_76px]">
                  <span className="min-w-0"><span className="block font-medium">{x.market}</span>{x.cal && <CalibLine cal={x.cal} className="block" />}</span>
                  <span className="hidden text-text-3 sm:block">{x.family}</span>
                  <div className="hidden items-center gap-2 sm:flex"><div className="h-1.5 w-20 rounded-full bg-surface-3"><div className="h-full rounded-full bg-brand/60" style={{ width: `${x.p * 100}%` }} /></div><span className="tabular">{pct(x.p)}</span></div>
                  <span className="tabular hidden text-right text-text-2 sm:block">{fairOdds(x.p)}</span>
                  <span className="flex items-center justify-end gap-2"><span className="tabular sm:hidden">{pct(x.p)}</span><span className={cn("rounded px-1.5 py-0.5 text-[10px] font-semibold", tierColor(x.tier))}>{x.tier.slice(4)}</span></span>
                </li>
              ))}
            </ul>
          </details>
        )}
        <p className="border-t border-border px-4 py-2 text-[11px] text-text-3">Moins de risque = probabilité plus élevée, pas une meilleure décision. Fiabilité des paliers : page AI Performance.</p>
      </Card>
    </div>
  );
}
