"use client";
import { CheckCircle2, CircleX } from "lucide-react";
import type { Performance, TeamLite } from "@/lib/types";
import { cn, pct } from "@/lib/utils";
import { TeamLogo } from "./football";
import { EmptyState } from "./ui/primitives";

type Row = Performance["history"][number];
const BG = { H: "bg-home", D: "bg-draw", A: "bg-away" } as const;
const prob = (r: Row, k: Row["predicted"]) => (k === "H" ? r.pH : k === "D" ? r.pD : r.pA);
const outcome = (r: Row, k: Row["predicted"]) => (k === "H" ? r.homeName : k === "A" ? r.awayName : "Nul");
const shortDate = (d: string) => new Date(d).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "2-digit" });

function Verdict({ ok, compact }: { ok: boolean; compact?: boolean }) {
  return ok ? (
    <span className="inline-flex items-center gap-1 rounded-full bg-good/10 px-2 py-0.5 text-[12px] font-medium text-good"><CheckCircle2 className="size-3.5" />{compact ? "" : "Correcte"}</span>
  ) : (
    <span className="inline-flex items-center gap-1 rounded-full bg-surface-2 px-2 py-0.5 text-[12px] font-medium text-text-3"><CircleX className="size-3.5" />{compact ? "" : "Incorrecte"}</span>
  );
}

/** Barre 1-X-2 miniature : la part de l'issue réelle est entourée. */
function MiniProbs({ r }: { r: Row }) {
  return (
    <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-surface-3" aria-hidden>
      {(["H", "D", "A"] as const).map((k) => (
        <span key={k} className={cn(BG[k], r.actual === k ? "opacity-100" : "opacity-35")} style={{ width: `${prob(r, k) * 100}%` }} />
      ))}
    </div>
  );
}

/** Historique des prédictions : Match · Prédiction · Probabilité · Résultat réel · Correct / Incorrect.
    Tableau à partir de md, cartes compactes en dessous (aucun défilement horizontal sur mobile). */
export function PredictionHistory({ rows, teams }: { rows: Row[]; teams: Record<string, TeamLite> }) {
  if (!rows.length) return <EmptyState title="Aucune prédiction évaluée pour l'instant" />;
  return (
    <div>
      <ul className="divide-y divide-border md:hidden">
        {rows.map((r, i) => (
          <li key={i} className="px-4 py-3">
            <div className="flex items-center justify-between gap-2 text-[11px] text-text-3">
              <span>{shortDate(r.date)}</span><Verdict ok={r.correct} />
            </div>
            <div className="mt-1.5 grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 text-[13px] font-medium">
              <span className="flex min-w-0 items-center gap-1.5"><TeamLogo team={teams[r.home]} size={18} /><span className="truncate">{r.homeName}</span></span>
              <span className="tabular rounded-md bg-surface-2 px-1.5 py-0.5 font-semibold">{r.score}</span>
              <span className="flex min-w-0 flex-row-reverse items-center gap-1.5 text-right"><TeamLogo team={teams[r.away]} size={18} /><span className="truncate">{r.awayName}</span></span>
            </div>
            <div className="mt-2"><MiniProbs r={r} /></div>
            <div className="tabular mt-1.5 flex justify-between gap-2 text-[11px] text-text-2">
              <span className="truncate">Prédit : <b className="font-semibold text-text">{outcome(r, r.predicted)}</b> {pct(prob(r, r.predicted))}</span>
              <span className="shrink-0">Réel : {outcome(r, r.actual)}</span>
            </div>
          </li>
        ))}
      </ul>
      <div className="hidden md:block">
        <table className="tabular w-full text-[13px]">
          <thead><tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-text-3">
            <th className="py-2 pl-4 font-medium">Match</th><th className="font-medium">Prédiction</th>
            <th className="w-44 font-medium">Probabilité</th><th className="font-medium">Résultat réel</th><th className="py-2 pr-4 text-right font-medium">Verdict</th>
          </tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-border transition-colors last:border-0 hover:bg-surface-2">
                <td className="py-2.5 pl-4">
                  <div className="flex items-center gap-1.5"><TeamLogo team={teams[r.home]} size={18} /><span className="max-w-[150px] truncate font-medium">{r.homeName}</span>
                    <span className="text-text-3">–</span><span className="max-w-[150px] truncate font-medium">{r.awayName}</span><TeamLogo team={teams[r.away]} size={18} /></div>
                  <div className="mt-0.5 text-[11px] text-text-3">{shortDate(r.date)}</div>
                </td>
                <td><span className="font-medium">{outcome(r, r.predicted)}</span></td>
                <td className="pr-4">
                  <div className="flex items-center gap-2"><span className="w-9 font-semibold">{pct(prob(r, r.predicted))}</span><div className="flex-1"><MiniProbs r={r} /></div></div>
                </td>
                <td><span className="rounded-md bg-surface-2 px-1.5 py-0.5 font-semibold">{r.score}</span> <span className="text-text-2">{outcome(r, r.actual)}</span></td>
                <td className="py-2.5 pr-4 text-right"><Verdict ok={r.correct} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="border-t border-border px-4 py-2 text-[11px] leading-relaxed text-text-3">
        La barre montre les probabilités 1 · X · 2 ; le segment opaque est l'issue réelle. Une issue à {pct(0.35)} se produit environ une fois sur trois : une prédiction incorrecte n'est pas forcément une erreur du modèle.
      </p>
    </div>
  );
}
