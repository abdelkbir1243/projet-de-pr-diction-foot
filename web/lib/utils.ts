import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export const cn = (...c: ClassValue[]) => twMerge(clsx(c));

export const pct = (p: number | null | undefined, digits = 0) => (p == null || Number.isNaN(p) ? "—" : `${(100 * p).toFixed(digits)} %`);
export const num = (x: number | null | undefined, digits = 1) => (x == null || Number.isNaN(x) ? "—" : x.toFixed(digits));
export const fairOdds = (p: number) => (p > 0 ? (1 / p).toFixed(2) : "—");

/** Date locale AAAA-MM-JJ (fuseau du navigateur). */
export function dayKey(d: Date | string) {
  const x = typeof d === "string" ? new Date(d) : d;
  return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}-${String(x.getDate()).padStart(2, "0")}`;
}
export function addDays(key: string, n: number) {
  const [y, m, d] = key.split("-").map(Number);
  return dayKey(new Date(y, m - 1, d + n));
}
export const timeOf = (iso: string, locale = "fr-FR") => new Date(iso).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
export function longDate(key: string, locale = "fr-FR") {
  const [y, m, d] = key.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(locale, { weekday: "long", day: "numeric", month: "long" });
}
export const shortDate = (iso: string, locale = "fr-FR") => new Date(iso).toLocaleDateString(locale, { day: "2-digit", month: "short", year: "2-digit" });

export const tierColor = (tier: string) =>
  tier.startsWith("1") ? "text-good bg-good-soft" : tier.startsWith("2") ? "text-brand-ink bg-brand-soft" : tier.startsWith("3") ? "text-text-2 bg-surface-2"
    : tier.startsWith("4") ? "text-warn bg-warn-soft" : "text-bad bg-live-soft";

/** Lien vers la page équipe, seulement si l'équipe a une page (championnats couverts, saison en cours). */
export const teamHref = (t: { slug: string; competition: string } | null | undefined) => (t && t.competition ? `/team/${t.slug}` : undefined);
