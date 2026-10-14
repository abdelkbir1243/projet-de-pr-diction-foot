"use client";
/* Composants « football » réutilisables : TeamLogo, FormGuide, ProbabilityBar, MatchStatusBadge, AIBadge, FavoriteStar, TeamLink. */
import Link from "next/link";
import type { ReactNode } from "react";
import { Sparkles, Star as StarIcon } from "lucide-react";
import type { LiveState, Result, TeamLite } from "@/lib/types";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { useFavorites } from "@/lib/favorites";

/* ───────────── Écusson ─────────────
   Forme de bouclier + code de l'équipe, couleur déterministe. Aucune reproduction des logos officiels. */
export function TeamLogo({ team, size = 28, className }: { team: Pick<TeamLite, "code" | "color" | "name"> | null | undefined; size?: number; className?: string }) {
  const color = team?.color ?? "#8a93a3";
  const code = team?.code ?? "?";
  const small = size < 22;
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" role="img" aria-label={team?.name ?? "Équipe"} className={cn("shrink-0", className)}>
      <path d="M16 1.5 29 6v9.2c0 7.3-5.4 13-13 15.3C8.4 28.2 3 22.5 3 15.2V6L16 1.5Z" fill={color} />
      <path d="M16 1.5 29 6v9.2c0 7.3-5.4 13-13 15.3V1.5Z" fill="#000" opacity="0.14" />
      <path d="M16 1.5 29 6v9.2c0 7.3-5.4 13-13 15.3C8.4 28.2 3 22.5 3 15.2V6L16 1.5Z" fill="none" stroke="#fff" strokeOpacity="0.25" strokeWidth="1" />
      <text x="16" y={small ? 21 : 19.5} textAnchor="middle" fontSize={small ? 14 : code.length > 2 ? 8.6 : 10} fontWeight={700} fill="#fff"
        fontFamily="var(--font-geist-sans), system-ui" letterSpacing="0.2">
        {small ? code[0] : code}
      </text>
    </svg>
  );
}

/* ───────────── Forme : badges V/N/D (W/D/L en anglais) ───────────── */
const RES_FR: Record<Result, string> = { W: "V", D: "N", L: "D" };
const RES_STYLE: Record<Result, string> = { W: "bg-good text-white", D: "bg-draw text-white", L: "bg-bad text-white" };
export type FormItem = { result: Result; title?: string };

export function FormGuide({ items, size = "sm", className }: { items: (Result | FormItem)[]; size?: "sm" | "md"; className?: string }) {
  const { lang } = useI18n();
  if (!items.length) return <span className="text-xs text-text-3">—</span>;
  const list = items.map((x) => (typeof x === "string" ? { result: x } : x));
  return (
    <span className={cn("inline-flex gap-1", className)} aria-label={`Forme : ${list.map((x) => x.result).join(" ")}`}>
      {list.map((x, i) => (
        <span key={i} title={x.title}
          className={cn("grid place-items-center rounded-md font-semibold tabular", RES_STYLE[x.result],
            size === "sm" ? "size-[18px] text-[10px]" : "size-7 text-xs", i === list.length - 1 && "ring-2 ring-offset-1 ring-offset-surface ring-border-strong")}>
          {lang === "fr" ? RES_FR[x.result] : x.result}
        </span>
      ))}
    </span>
  );
}
/** Compatibilité : ancienne API. */
export const FormIndicator = ({ form, size }: { form: Result[]; size?: "sm" | "md" }) => <FormGuide items={form} size={size} />;

/* ───────────── Barre de probabilités 1 · X · 2 ───────────── */
export function ProbabilityBar({ home, draw, away, labels, variant = "full", animate = true }: {
  home: number; draw: number; away: number; labels?: [ReactNode, ReactNode, ReactNode]; variant?: "full" | "compact" | "mini"; animate?: boolean;
}) {
  const segs = [
    { v: home, c: "bg-home", t: "text-home", l: labels?.[0] ?? "1" },
    { v: draw, c: "bg-draw", t: "text-text-2", l: labels?.[1] ?? "X" },
    { v: away, c: "bg-away", t: "text-away", l: labels?.[2] ?? "2" },
  ];
  const max = Math.max(home, draw, away);
  const bar = (
    <div className={cn("flex w-full gap-[3px] overflow-hidden rounded-full", variant === "full" ? "h-3" : variant === "compact" ? "h-2" : "h-1.5")}
      role="img" aria-label={`Probabilités : 1 ${Math.round(home * 100)} %, X ${Math.round(draw * 100)} %, 2 ${Math.round(away * 100)} %`}>
      {segs.map((s, i) => (
        <div key={i} className={cn(s.c, "h-full rounded-[2px] transition-[width,opacity] duration-500", s.v !== max && "opacity-55", animate && "bar-grow")}
          style={{ width: `${s.v * 100}%`, animationDelay: `${i * 60}ms` }} />
      ))}
    </div>
  );
  if (variant === "mini") return bar;
  return (
    <div className="w-full">
      {variant === "full" && (
        <div className="tabular mb-2 grid grid-cols-3 items-end">
          {segs.map((s, i) => (
            <div key={i} className={cn("min-w-0", i === 1 && "text-center", i === 2 && "text-right")}>
              <div className={cn("text-2xl font-semibold leading-none tracking-tight", s.v === max ? s.t : "text-text-2")}>{Math.round(s.v * 100)}<span className="text-sm font-medium">%</span></div>
              <div className="mt-1 truncate text-[11px] font-medium uppercase tracking-wide text-text-3">{s.l}</div>
            </div>
          ))}
        </div>
      )}
      {bar}
      {variant === "compact" && (
        <div className="tabular mt-1 flex justify-between text-[11px] text-text-3">
          {segs.map((s, i) => <span key={i} className={cn(s.v === max && cn("font-semibold", s.t))}>{Math.round(s.v * 100)}</span>)}
        </div>
      )}
    </div>
  );
}
/** Compatibilité : ancienne API (compact = barre seule). */
export const PredictionBar = ({ home, draw, away, labels, compact }: { home: number; draw: number; away: number; labels?: [string, string, string]; compact?: boolean }) =>
  <ProbabilityBar home={home} draw={draw} away={away} labels={labels} variant={compact ? "mini" : "full"} />;

/* ───────────── Statut du match ───────────── */
export function MatchStatusBadge({ state, kickoff, size = "sm", timeKnown = true }: { state: LiveState; kickoff: string; size?: "sm" | "md"; timeKnown?: boolean }) {
  const { t, locale } = useI18n();
  const base = size === "md" ? "text-[13px] px-2 py-0.5" : "text-[11px] px-1.5 py-px";
  if (state.status === "live")
    return (
      <span className={cn("inline-flex items-center gap-1 rounded-md bg-live-soft font-semibold text-live", base)}>
        <span className="size-1.5 animate-pulse-dot rounded-full bg-live" />{state.minute ? `${state.minute}'` : "LIVE"}
      </span>
    );
  if (state.status === "halftime") return <span className={cn("rounded-md bg-live-soft font-semibold text-live", base)}>{t("status.halftime")}</span>;
  if (state.status === "finished") return <span className={cn("rounded-md bg-surface-2 font-medium text-text-3", base)}>{t("status.finished")}</span>;
  if (state.status === "postponed") return <span className={cn("rounded-md bg-warn-soft font-medium text-warn", base)}>{t("status.postponed")}</span>;
  if (state.status === "cancelled") return <span className={cn("rounded-md bg-surface-2 font-medium text-text-3 line-through", base)}>{t("status.cancelled")}</span>;
  if (state.awaiting) return <span className={cn("rounded-md bg-surface-2 font-medium text-text-2", base)} title="Coup d'envoi passé : le résultat sera publié à la prochaine mise à jour">En attente</span>;
  if (!timeKnown) return <span className={cn("tabular font-semibold text-text-3", size === "md" ? "text-base" : "text-[13px]")} title="Horaire exact non communiqué par la source">--:--</span>;
  return (
    <span className={cn("tabular font-semibold text-text", size === "md" ? "text-base" : "text-[13px]")} suppressHydrationWarning>
      {new Date(kickoff).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })}
    </span>
  );
}
/** Compatibilité : ancienne API. */
export const StatusPill = MatchStatusBadge;

export function AIBadge({ label = "AI", className }: { label?: string; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-md bg-brand-soft px-1.5 py-px text-[10px] font-bold uppercase tracking-wide text-brand-ink", className)}>
      <Sparkles className="size-3" />{label}
    </span>
  );
}

export function FavoriteStar({ kind, id, label, className }: { kind: "teams" | "matches"; id: string; label: string; className?: string }) {
  const fav = useFavorites(kind);
  const on = fav.has(id);
  return (
    <button type="button" onClick={(e) => { e.preventDefault(); e.stopPropagation(); fav.toggle(id); }} aria-pressed={on}
      aria-label={on ? `Retirer ${label} des favoris` : `Ajouter ${label} aux favoris`}
      className={cn("relative z-10 grid size-9 place-items-center rounded-lg text-text-3 transition-[color,background,transform] hover:bg-surface-2 hover:text-warn active:scale-90", on && "text-warn", className)}>
      <StarIcon className="size-4" fill={on ? "currentColor" : "none"} />
    </button>
  );
}

/** Lien vers une équipe si elle a une page ; sinon simple texte (équipe reléguée, hors périmètre). */
export function TeamLink({ team, slug, className, children }: { team: TeamLite | null | undefined; slug: string; className?: string; children: ReactNode }) {
  return team?.competition ? <Link href={`/team/${slug}`} className={cn("hover:underline", className)}>{children}</Link> : <span className={className}>{children}</span>;
}
