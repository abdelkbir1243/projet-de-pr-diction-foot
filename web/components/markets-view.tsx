"use client";
/* Cotes & risque : toutes les issues des prochains matchs classées du moins risqué au plus risqué, avec la cote juste du modèle,
   la cote du marché quand elle existe, et la fiabilité observée de chaque palier. Outil d'analyse, pas de conseil de pari. */
import Link from "next/link";
import { useMemo, useState } from "react";
import { AlertTriangle, Scale, ShieldCheck } from "lucide-react";
import type { Competition, MarketRow, MarketsFile, MatchSummary, Prediction, TeamLite } from "@/lib/types";
import { cn, pct, tierColor } from "@/lib/utils";
import { ProbabilityBar, TeamLogo } from "./football";
import { Badge, Card, CardHeader, EmptyState } from "./ui/primitives";

const FAMILLES = ["Toutes", "Résultat", "Double chance", "Buts", "Corners", "Cartons"] as const;
const PALIERS = ["Tous", "1", "2", "3", "4", "5"] as const;
const NOM_PALIER: Record<string, string> = { "1": "Très faible", "2": "Faible", "3": "Modéré", "4": "Élevé", "5": "Très élevé" };

export type Disagreement = Pick<MatchSummary, "slug" | "homeName" | "awayName" | "home" | "away" | "kickoff" | "competition"> & { market: NonNullable<Prediction["market"]>; model: [number, number, number] };

export function MarketsView({ data, competitions, teams, disagreements }: { data: MarketsFile; competitions: Competition[]; teams: Record<string, TeamLite>; disagreements: Disagreement[] }) {
  const [fam, setFam] = useState<(typeof FAMILLES)[number]>("Toutes");
  const [tier, setTier] = useState<(typeof PALIERS)[number]>("Tous");
  const [comp, setComp] = useState("all");
  const [n, setN] = useState(40);
  const rows = useMemo(() => data.rows.filter((r) => (fam === "Toutes" || r.family === fam) && (tier === "Tous" || r.tier.startsWith(tier)) && (comp === "all" || r.competition === comp)),
    [data.rows, fam, tier, comp]);
  const covered = competitions.filter((c) => c.covered || c.model === "cup");
  return (
    <div className="space-y-5">
      <Card className="flex gap-3 border-warn/30 bg-warn-soft/40 p-4 text-[13px] leading-relaxed text-text-2">
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warn" />
        <p>Le « risque » est la probabilité que l&apos;issue <b>ne se réalise pas</b> selon le modèle. Une issue peu risquée n&apos;est pas une bonne affaire : sur 2021-2026, <b>aucun palier n&apos;a été rentable aux cotes réelles</b>, et les cotes restent en moyenne plus précises que le modèle. Cette page sert à comprendre les probabilités, pas à parier.</p>
      </Card>

      {data.tiers && (
        <Card>
          <CardHeader title="Fiabilité des paliers de risque" subtitle="Toutes les issues de 30 marchés, matchs 2021-2026 hors échantillon" icon={<ShieldCheck className="size-4 text-brand" />} />
          <div className="snap-row px-4 pb-4 md:grid md:grid-cols-5 [&>*]:w-[46%] md:[&>*]:w-auto">
            {data.tiers.map((t) => (
              <div key={t.tier} className="min-w-0 rounded-xl border border-border bg-surface px-3 py-3">
                <span className={cn("rounded px-1.5 py-0.5 text-[11px] font-semibold", tierColor(t.tier))}>{t.tier.slice(4)}</span>
                <div className="tabular mt-2 text-[13px]">Annoncé <b>{pct(t.predicted, 1)}</b></div>
                <div className="tabular text-[13px]">Réalisé <b>{pct(t.observed, 1)}</b></div>
                <div className={cn("tabular mt-1 text-[12px] font-medium", t.returnAtOdds < 0 ? "text-bad" : "text-good")}>Rendement aux cotes {(t.returnAtOdds * 100).toFixed(1)} %</div>
                <div className="tabular mt-0.5 text-[11px] text-text-3">{t.decisions.toLocaleString("fr-FR")} issues</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {disagreements.length > 0 && (
        <Card>
          <CardHeader title="Désaccords modèle / marché" subtitle="Matchs où les probabilités du modèle s'écartent le plus de celles des cotes" icon={<Scale className="size-4 text-brand" />} />
          <ul className="divide-y divide-border">
            {disagreements.map((d) => (
              <li key={d.slug}>
                <Link href={`/match/${d.slug}?tab=market`} className="grid gap-2 px-4 py-3 transition-colors hover:bg-surface-2 sm:grid-cols-[minmax(0,1fr)_200px_200px_auto] sm:items-center">
                  <span className="flex min-w-0 items-center gap-2 text-[13px] font-medium">
                    <TeamLogo team={d.home ? teams[d.home] : null} size={18} /><span className="truncate">{d.homeName} – {d.awayName}</span>
                  </span>
                  <span><span className="label-caps">Modèle</span><ProbabilityBar home={d.model[0]} draw={d.model[1]} away={d.model[2]} variant="mini" /></span>
                  <span><span className="label-caps">Marché</span><ProbabilityBar home={d.market.home} draw={d.market.draw} away={d.market.away} variant="mini" /></span>
                  <Badge tone={d.market.agreement === "désaccord marqué" ? "live" : "warn"} className="justify-self-start">{d.market.agreement}</Badge>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="space-y-2">
        <div className="snap-row -mx-3 px-3 sm:mx-0 sm:flex-wrap sm:px-0">
          {FAMILLES.map((f) => <Chip key={f} on={fam === f} onClick={() => setFam(f)}>{f}</Chip>)}
        </div>
        <div className="snap-row -mx-3 px-3 sm:mx-0 sm:flex-wrap sm:px-0">
          {PALIERS.map((p) => <Chip key={p} on={tier === p} onClick={() => setTier(p)}>{p === "Tous" ? "Tous les risques" : `Risque ${NOM_PALIER[p].toLowerCase()}`}</Chip>)}
          <select value={comp} onChange={(e) => setComp(e.target.value)} aria-label="Compétition" className="h-8 shrink-0 rounded-full border border-border bg-surface px-3 text-[13px] text-text-2">
            <option value="all">Toutes les compétitions</option>
            {covered.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
          </select>
        </div>
      </div>

      <Card>
        <CardHeader title={`${rows.length} issues · du moins risqué au plus risqué`} subtitle="Cote juste = 1 / probabilité du modèle. Cote et probabilité du marché : 1X2 et +2,5 buts uniquement." />
        {rows.length === 0 ? <EmptyState title="Aucune issue pour ces filtres" hint="Les marchés sont calculés pour les matchs à venir des 5 grands championnats." /> : (
          <>
            <ul className="divide-y divide-border md:hidden">{rows.slice(0, n).map((r, i) => <MobileRow key={i} r={r} teams={teams} />)}</ul>
            <div className="hidden md:block">
              <table className="tabular w-full text-[13px]">
                <thead><tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-text-3">
                  <th className="py-2 pl-4 font-medium">Match</th><th className="font-medium">Issue</th><th className="w-40 font-medium">Probabilité</th>
                  <th className="font-medium">Risque</th><th className="text-right font-medium">Cote juste</th><th className="text-right font-medium">Cote marché</th><th className="py-2 pr-4 text-right font-medium">Écart</th>
                </tr></thead>
                <tbody>
                  {rows.slice(0, n).map((r, i) => (
                    <tr key={i} className="border-b border-border transition-colors last:border-0 hover:bg-surface-2">
                      <td className="py-2.5 pl-4"><Link href={`/match/${r.match}?tab=market`} className="flex items-center gap-1.5 font-medium hover:text-brand"><TeamLogo team={teams[r.home]} size={16} /><span className="max-w-[220px] truncate">{r.homeName} – {r.awayName}</span></Link>
                        <div className="text-[11px] text-text-3" suppressHydrationWarning>{new Date(r.kickoff).toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" })}</div></td>
                      <td className="text-text-2">{r.market}</td>
                      <td className="pr-4"><div className="flex items-center gap-2"><span className="w-10 font-semibold">{pct(r.p)}</span><div className="h-1.5 flex-1 rounded-full bg-surface-3"><div className="bar-grow h-full rounded-full bg-brand" style={{ width: `${r.p * 100}%` }} /></div></div></td>
                      <td><span className={cn("rounded px-1.5 py-0.5 text-[11px] font-semibold", tierColor(r.tier))}>{r.tier.slice(4)}</span></td>
                      <td className="text-right">{r.fairOdds.toFixed(2)}</td>
                      <td className="text-right">{r.odds ? r.odds.toFixed(2) : <span className="text-text-3">—</span>}</td>
                      <td className="py-2.5 pr-4 text-right">{r.marketP != null ? <Gap v={r.p - r.marketP} /> : <span className="text-text-3">—</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {rows.length > n && <button onClick={() => setN(n + 40)} className="w-full border-t border-border py-2.5 text-[13px] font-medium text-brand hover:bg-surface-2">Afficher plus ({rows.length - n} restantes)</button>}
          </>
        )}
      </Card>
    </div>
  );
}

function Gap({ v }: { v: number }) {
  return <span className={cn("font-medium", Math.abs(v) < 0.03 ? "text-text-3" : v > 0 ? "text-good" : "text-bad")}>{v > 0 ? "+" : ""}{(100 * v).toFixed(1)} pts</span>;
}

function MobileRow({ r, teams }: { r: MarketRow; teams: Record<string, TeamLite> }) {
  return (
    <li>
      <Link href={`/match/${r.match}?tab=market`} className="block px-4 py-3">
        <div className="flex items-center justify-between gap-2 text-[11px] text-text-3">
          <span className="flex min-w-0 items-center gap-1.5"><TeamLogo team={teams[r.home]} size={14} /><span className="truncate">{r.homeName} – {r.awayName}</span></span>
          <span className={cn("shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold", tierColor(r.tier))}>{r.tier.slice(4)}</span>
        </div>
        <div className="mt-1 flex items-baseline justify-between gap-2">
          <span className="truncate text-[13px] font-medium">{r.market}</span><span className="tabular text-[15px] font-semibold">{pct(r.p)}</span>
        </div>
        <div className="tabular mt-1 flex justify-between text-[11px] text-text-2">
          <span>Cote juste {r.fairOdds.toFixed(2)}{r.odds ? ` · marché ${r.odds.toFixed(2)}` : ""}</span>{r.marketP != null && <Gap v={r.p - r.marketP} />}
        </div>
      </Link>
    </li>
  );
}

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} className={cn("inline-flex h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border px-3 text-[13px] font-medium transition-colors active:scale-95",
      on ? "border-brand bg-brand-soft text-brand-ink" : "border-border bg-surface text-text-2 hover:border-border-strong hover:text-text")}>{children}</button>
  );
}

