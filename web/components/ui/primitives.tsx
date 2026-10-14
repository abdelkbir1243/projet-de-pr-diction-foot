import type { ComponentProps, ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Card({ className, interactive, ...p }: ComponentProps<"section"> & { interactive?: boolean }) {
  return <section className={cn("min-w-0 rounded-xl border border-border bg-surface shadow-card", interactive && "card-hover", className)} {...p} />;
}

export function CardHeader({ title, subtitle, action, icon, className }: { title: ReactNode; subtitle?: ReactNode; action?: ReactNode; icon?: ReactNode; className?: string }) {
  return (
    <header className={cn("flex items-center justify-between gap-3 px-4 pb-2 pt-3.5", className)}>
      <div className="flex min-w-0 items-center gap-2">
        {icon}
        <div className="min-w-0">
          <h2 className="truncate text-[12px] font-semibold uppercase tracking-[0.06em] text-text-2">{title}</h2>
          {subtitle && <p className="mt-0.5 truncate text-xs text-text-3">{subtitle}</p>}
        </div>
      </div>
      {action}
    </header>
  );
}

export function Badge({ className, tone = "neutral", ...p }: ComponentProps<"span"> & { tone?: "neutral" | "brand" | "live" | "good" | "warn" | "outline" }) {
  const tones = {
    neutral: "bg-surface-2 text-text-2",
    brand: "bg-brand-soft text-brand-ink",
    live: "bg-live-soft text-live",
    good: "bg-good-soft text-good",
    warn: "bg-warn-soft text-warn",
    outline: "border border-border text-text-2",
  };
  return <span className={cn("inline-flex items-center gap-1 whitespace-nowrap rounded-md px-1.5 py-0.5 text-[11px] font-medium", tones[tone], className)} {...p} />;
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("skeleton h-4 w-full", className)} />;
}

/** Carte squelette générique (chargement). */
export function SkeletonCard({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn("rounded-xl border border-border bg-surface p-4", className)} aria-hidden>
      <Skeleton className="h-3 w-28" />
      <div className="mt-4 space-y-2.5">{Array.from({ length: lines }).map((_, i) => <Skeleton key={i} className={cn("h-4", i % 2 ? "w-2/3" : "w-full")} />)}</div>
    </div>
  );
}

/** État vide / erreur / indisponible — toujours une explication, jamais une zone vide. */
export function EmptyState({ icon, title, hint, action, tone = "neutral", className }: {
  icon?: ReactNode; title: ReactNode; hint?: ReactNode; action?: ReactNode; tone?: "neutral" | "warn" | "error"; className?: string;
}) {
  const ring = tone === "error" ? "bg-live-soft text-live" : tone === "warn" ? "bg-warn-soft text-warn" : "bg-surface-2 text-text-3";
  return (
    <div className={cn("flex flex-col items-center justify-center gap-2 px-6 py-10 text-center", className)} role={tone === "error" ? "alert" : undefined}>
      {icon && <div className={cn("mb-1 grid size-11 place-items-center rounded-full", ring)}>{icon}</div>}
      <p className="text-sm font-semibold text-text">{title}</p>
      {hint && <p className="max-w-md text-xs leading-relaxed text-text-3">{hint}</p>}
      {action}
    </div>
  );
}

/** StatsCard : une valeur clé, son libellé et une précision. `bar` (0-1) ajoute une jauge. */
export function Stat({ label, value, sub, bar, tone = "brand", className }: { label: ReactNode; value: ReactNode; sub?: ReactNode; bar?: number | null; tone?: "brand" | "home" | "away"; className?: string }) {
  const c = tone === "home" ? "bg-home" : tone === "away" ? "bg-away" : "bg-brand";
  return (
    <div className={cn("min-w-0 rounded-xl border border-border bg-surface px-3.5 py-3", className)}>
      <div className="truncate text-[11px] font-medium uppercase tracking-wide text-text-3">{label}</div>
      <div className="tabular mt-1 text-xl font-semibold tracking-tight text-text">{value}</div>
      {bar != null && <div className="mt-2 h-1 rounded-full bg-surface-3"><div className={cn("bar-grow h-full rounded-full", c)} style={{ width: `${Math.max(0, Math.min(1, bar)) * 100}%` }} /></div>}
      {sub && <div className="mt-1 truncate text-xs text-text-3">{sub}</div>}
    </div>
  );
}
export const StatsCard = Stat;

export function PageHeader({ title, subtitle, eyebrow, children }: { title: ReactNode; subtitle?: ReactNode; eyebrow?: ReactNode; children?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        {eyebrow && <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-brand">{eyebrow}</div>}
        <h1 className="text-xl font-semibold tracking-tight text-text sm:text-2xl">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-sm text-text-2">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

/** Pastille de compétition (code pays), sans logo officiel. */
export function CompetitionMark({ cc, size = 20 }: { cc: string; size?: number }) {
  return (
    <span className="inline-grid shrink-0 place-items-center rounded-md bg-text font-mono text-[9px] font-bold tracking-tight text-surface" style={{ width: size + 8, height: size }} aria-hidden>
      {cc}
    </span>
  );
}
