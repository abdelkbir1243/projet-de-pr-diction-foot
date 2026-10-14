"use client";
/* Degré de confiance : niveau A/B/C d'un match, preuve historique (hors échantillon) et calibration d'une statistique. */
import { CircleCheck, CircleMinus, CircleAlert, ShieldCheck } from "lucide-react";
import type { Calib, Trust, TrustLevel } from "@/lib/types";
import { cn, pct } from "@/lib/utils";
import { Card, CardHeader } from "./ui/primitives";

export const LEVEL_STYLE: Record<TrustLevel, string> = {
  A: "bg-good-soft text-good", B: "bg-warn-soft text-warn", C: "bg-live-soft text-live",
};
const LEVEL_NAME: Record<TrustLevel, string> = { A: "élevé", B: "moyen", C: "faible" };

export function LevelChip({ level, className, long }: { level: TrustLevel; className?: string; long?: boolean }) {
  return (
    <span title={`Degré de confiance ${LEVEL_NAME[level]}`}
      className={cn("inline-flex items-center gap-1 rounded-md px-1.5 py-px text-[10px] font-bold uppercase tracking-wide", LEVEL_STYLE[level], className)}>
      <ShieldCheck className="size-3" />{long ? `Confiance ${LEVEL_NAME[level]}` : level}
    </span>
  );
}

/** « Annoncé 61 % → réalisé 60 % [58-62] sur 4 100 cas » */
export function CalibLine({ cal, className }: { cal: Calib; className?: string }) {
  const ok = cal.announced >= cal.lo && cal.announced <= cal.hi;
  return (
    <span className={cn("tabular text-[11px] text-text-3", className)} title={`Classe de probabilité : ${cal.n.toLocaleString("fr-FR")} cas passés hors échantillon`}>
      réalisé {pct(cal.observed)} <span className="text-text-3/80">[{Math.round(cal.lo * 100)}–{Math.round(cal.hi * 100)}]</span>
      <span className={cn("ml-1", ok ? "text-good" : "text-warn")}>{ok ? "●" : "◐"}</span>
    </span>
  );
}

export function TrustCard({ trust, compact }: { trust: Trust; compact?: boolean }) {
  const e = trust.evidence;
  const Icon = { plus: CircleCheck, minus: CircleAlert, neutral: CircleMinus };
  return (
    <Card>
      <CardHeader title="Degré de confiance" subtitle="Mesuré sur des matchs que le modèle n'avait pas vus, mis à jour à chaque publication"
        icon={<ShieldCheck className="size-4 text-brand" />} action={<LevelChip level={trust.level} long />} />
      <div className={cn("grid gap-4 px-4 pb-4", !compact && "md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]")}>
        <div className="rounded-xl bg-surface-2 p-3.5">
          <div className="text-[13px] text-text-2">Favori du modèle : <b className="text-text">{trust.favorite}</b> à <b className="tabular text-text">{pct(trust.p)}</b></div>
          {e ? (
            <>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="tabular text-2xl font-semibold">{pct(e.observed)}</span>
                <span className="text-[12px] text-text-2">de réussite observée</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-surface-3" aria-hidden>
                <div className="relative h-full">
                  <div className="absolute inset-y-0 rounded-full bg-brand/30" style={{ left: `${e.lo * 100}%`, width: `${(e.hi - e.lo) * 100}%` }} />
                  <div className="absolute inset-y-[-2px] w-0.5 rounded bg-brand" style={{ left: `${e.observed * 100}%` }} />
                  <div className="absolute inset-y-[-3px] w-0.5 rounded bg-text-3" style={{ left: `${trust.p * 100}%` }} title="Probabilité annoncée" />
                </div>
              </div>
              <p className="mt-2 text-[12px] leading-relaxed text-text-2">
                Dans <b>{e.n.toLocaleString("fr-FR")} matchs</b> du même niveau ({trust.label.toLowerCase()}) où le favori était annoncé entre {Math.round(e.from * 100)} et {Math.round(e.to * 100)} %,
                il l&apos;a emporté {pct(e.observed)} du temps (IC 95 % : {Math.round(e.lo * 100)}–{Math.round(e.hi * 100)} %).
              </p>
            </>
          ) : <p className="mt-2 text-[12px] text-text-3">Trop peu de cas comparables pour publier un taux observé.</p>}
        </div>
        <ul className="space-y-2.5">
          {trust.factors.map((f) => {
            const I = Icon[f.effect];
            return (
              <li key={f.label} className="flex gap-2.5 text-[13px]">
                <I className={cn("mt-0.5 size-4 shrink-0", f.effect === "plus" ? "text-good" : f.effect === "minus" ? "text-warn" : "text-text-3")} />
                <span><span className="font-medium text-text">{f.label}</span><span className="block text-[12px] text-text-3">{f.detail}</span></span>
              </li>
            );
          })}
        </ul>
      </div>
      <p className="border-t border-border px-4 py-2 text-[11px] leading-relaxed text-text-3">
        Niveau A : modèle d&apos;accord avec les cotes (écart &lt; 5 points) et saison installée · B : désaccord modéré ou début de saison · C : désaccord marqué (≥ 10 points).
        Les facteurs retenus sont ceux dont l&apos;effet sur la fiabilité est démontré sur 2012-2026.
      </p>
    </Card>
  );
}
