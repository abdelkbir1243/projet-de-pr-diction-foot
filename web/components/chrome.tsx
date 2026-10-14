"use client";
/* Structure de l'application : Navbar, recherche globale, assistant, thème, Sidebar, MobileNav, Footer, bandeau de mode. */
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import * as DM from "@radix-ui/react-dropdown-menu";
import { useTheme } from "next-themes";
import {
  Activity, BarChart3, BrainCircuit, Calendar, ChevronRight, ChevronsLeft, ChevronsRight, Gauge, Home, Moon, Scale, Search, Shield, Sparkles, Star, Sun, Trophy, User, Users, X,
} from "lucide-react";
import type { Competition, DataMode, Meta, TeamLite } from "@/lib/types";
import { useI18n, type TKey } from "@/lib/i18n";
import { useFavorites } from "@/lib/favorites";
import { cn } from "@/lib/utils";
import { ProbabilityBar, TeamLogo } from "./football";
import { CompetitionMark } from "./ui/primitives";
import { AssistantButton, useAssistant } from "./assistant";

export interface SearchIndex {
  teams: TeamLite[];
  competitions: Pick<Competition, "slug" | "name" | "cc" | "country">[];
  matches: { slug: string; homeName: string; awayName: string; kickoff: string; competition: string; home: string | null; away: string | null }[];
}

export function Logo({ className }: { className?: string }) {
  return (
    <Link href="/" className={cn("flex items-center gap-2", className)} aria-label="Goalgebra — accueil">
      <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden>
        <defs><linearGradient id="lg-logo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="var(--brand)" /><stop offset="1" stopColor="var(--brand-2)" /></linearGradient></defs>
        <rect width="32" height="32" rx="9" fill="url(#lg-logo)" />
        <path d="M7 22.5c3.6-9.6 8.4-12.8 13-12.8" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" />
        <path d="M7 22.5h18" stroke="#fff" strokeWidth="1.4" strokeLinecap="round" opacity=".45" />
        <circle cx="23" cy="9.7" r="2.8" fill="#fff" />
      </svg>
      <span className="text-[17px] font-semibold tracking-tight text-text">
        Goal<span className="ai-text">gebra</span>
      </span>
    </Link>
  );
}

const NAV: { href: string; k: TKey; match: (p: string) => boolean }[] = [
  { href: "/", k: "nav.matches", match: (p) => p === "/" || p.startsWith("/matches") || p.startsWith("/match/") },
  { href: "/competitions", k: "nav.competitions", match: (p) => p.startsWith("/competition") || p.startsWith("/standings") },
  { href: "/predictions", k: "nav.predictions", match: (p) => p.startsWith("/predictions") },
  { href: "/markets", k: "nav.markets", match: (p) => p.startsWith("/markets") },
  { href: "/statistics", k: "nav.stats", match: (p) => p.startsWith("/statistics") || p.startsWith("/ai-performance") },
  { href: "/teams", k: "nav.teams", match: (p) => p.startsWith("/team") },
];

/* ───────────── Navbar ───────────── */
export function Navbar({ index }: { index: SearchIndex }) {
  const path = usePathname();
  const { t } = useI18n();
  const [searchOpen, setSearchOpen] = useState(false);
  useEffect(() => {
    const on = (e: KeyboardEvent) => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setSearchOpen(true); } };
    window.addEventListener("keydown", on); return () => window.removeEventListener("keydown", on);
  }, []);
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-surface/80 backdrop-blur-xl supports-[backdrop-filter]:bg-surface/70">
      <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-2 px-3 sm:px-4 lg:px-6">
        <Logo />
        <nav className="ml-3 hidden items-center md:flex lg:ml-6" aria-label="Navigation principale">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} aria-current={n.match(path) ? "page" : undefined}
              className={cn("relative px-3 py-4 text-[13px] font-medium transition-colors",
                n.match(path) ? "text-text after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:bg-brand" : "text-text-2 hover:text-text")}>
              {t(n.k)}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-0.5 sm:gap-1">
          <SearchBar onOpen={() => setSearchOpen(true)} />
          <AssistantButton />
          <ThemeToggle />
          <ProfileMenu />
        </div>
      </div>
      <SearchDialog open={searchOpen} onOpenChange={setSearchOpen} index={index} />
    </header>
  );
}

/** Champ de recherche (déclencheur) — la recherche s'ouvre en palette de commandes (⌘K). */
export function SearchBar({ onOpen }: { onOpen: () => void }) {
  const { t } = useI18n();
  return (
    <>
      <button onClick={onOpen}
        className="hidden h-9 w-64 items-center gap-2 rounded-lg border border-border bg-surface-2/70 px-3 text-left text-[13px] text-text-3 transition-colors hover:border-border-strong hover:bg-surface-2 lg:flex">
        <Search className="size-4" /><span className="flex-1 truncate">{t("search.placeholder")}</span>
        <kbd className="rounded border border-border bg-surface px-1 font-mono text-[10px]">⌘K</kbd>
      </button>
      <IconButton label="Rechercher" onClick={onOpen} className="lg:hidden"><Search className="size-[18px]" /></IconButton>
    </>
  );
}

/** Menu profil : profil, favoris, performance IA, assistant. */
function ProfileMenu() {
  const { t } = useI18n();
  const { setOpen } = useAssistant();
  const item = "flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] text-text-2 outline-none data-[highlighted]:bg-surface-2 data-[highlighted]:text-text";
  return (
    <>
      <DM.Root>
        <DM.Trigger asChild>
          <button aria-label={t("nav.profile")} className="ml-0.5 grid size-9 place-items-center rounded-full ai-gradient text-white shadow-card transition-transform hover:scale-105">
            <User className="size-[17px]" />
          </button>
        </DM.Trigger>
        <DM.Portal>
          <DM.Content align="end" sideOffset={8} className="z-50 w-60 animate-fade-in rounded-xl border border-border bg-surface p-1.5 shadow-pop">
            <div className="px-2.5 pb-2 pt-1.5"><div className="text-[13px] font-semibold">Invité</div><div className="text-xs text-text-3">Favoris enregistrés sur cet appareil</div></div>
            <DM.Separator className="my-1 h-px bg-border" />
            <DM.Item asChild className={item}><Link href="/profile"><User className="size-4" />{t("nav.profile")}</Link></DM.Item>
            <DM.Item asChild className={item}><Link href="/profile"><Star className="size-4" />{t("nav.favorites")}</Link></DM.Item>
            <DM.Item asChild className={item}><Link href="/ai-performance"><Gauge className="size-4" />{t("nav.performance")}</Link></DM.Item>
            <DM.Item asChild className={item}><Link href="/markets"><Scale className="size-4" />{t("nav.markets")}</Link></DM.Item>
            <DM.Separator className="my-1 h-px bg-border" />
            <DM.Item className={cn(item, "text-brand")} onSelect={() => setOpen(true)}><Sparkles className="size-4" />Assistant statistique</DM.Item>
          </DM.Content>
        </DM.Portal>
      </DM.Root>
    </>
  );
}

function IconButton({ label, children, className, ...p }: { label: string; children: ReactNode; className?: string } & React.ComponentProps<"button">) {
  return (
    <button aria-label={label} title={label} className={cn("grid size-9 place-items-center rounded-lg text-text-2 transition-colors hover:bg-surface-2 hover:text-text", className)} {...p}>
      {children}
    </button>
  );
}

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const dark = mounted && resolvedTheme === "dark";
  return (
    <IconButton label={dark ? "Passer en mode clair" : "Passer en mode sombre"} onClick={() => setTheme(dark ? "light" : "dark")}>
      {mounted ? (dark ? <Sun className="size-[18px]" /> : <Moon className="size-[18px]" />) : <span className="size-[18px]" />}
    </IconButton>
  );
}


/* ───────────── Recherche globale ───────────── */
const norm = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

function SearchDialog({ open, onOpenChange, index }: { open: boolean; onOpenChange: (o: boolean) => void; index: SearchIndex }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const results = useMemo(() => {
    const n = norm(q.trim());
    if (!n) return { teams: index.teams.slice(0, 0), competitions: index.competitions, matches: [] as SearchIndex["matches"] };
    return {
      teams: index.teams.filter((x) => norm(`${x.name} ${x.short} ${x.code}`).includes(n)).slice(0, 6),
      competitions: index.competitions.filter((x) => norm(`${x.name} ${x.country}`).includes(n)).slice(0, 4),
      matches: index.matches.filter((x) => norm(`${x.homeName} ${x.awayName}`).includes(n)).slice(0, 5),
    };
  }, [q, index]);
  const flat = [
    ...results.teams.map((x) => ({ href: `/team/${x.slug}`, key: x.slug })),
    ...results.competitions.map((x) => ({ href: `/competition/${x.slug}`, key: x.slug })),
    ...results.matches.map((x) => ({ href: `/match/${x.slug}`, key: x.slug })),
  ];
  useEffect(() => setSel(0), [q]);
  const go = (href: string) => { onOpenChange(false); setQ(""); router.push(href); };
  let i = -1;
  const item = (href: string, content: ReactNode) => {
    i++; const idx = i;
    return (
      <li key={href}>
        <button onMouseEnter={() => setSel(idx)} onClick={() => go(href)}
          className={cn("flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm", sel === idx ? "bg-surface-2" : "")}>
          {content}<ChevronRight className="ml-auto size-4 text-text-3" />
        </button>
      </li>
    );
  };
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" />
        <Dialog.Content onOpenAutoFocus={(e) => { e.preventDefault(); inputRef.current?.focus(); }}
          className="fixed left-1/2 top-[12vh] z-50 w-[calc(100%-24px)] max-w-xl -translate-x-1/2 animate-fade-in overflow-hidden rounded-2xl border border-border bg-surface shadow-pop">
          <Dialog.Title className="sr-only">Recherche</Dialog.Title>
          <div className="flex items-center gap-2 border-b border-border px-4">
            <Search className="size-4 text-text-3" />
            <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("search.placeholder")}
              onKeyDown={(e) => {
                if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(s + 1, flat.length - 1)); }
                if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)); }
                if (e.key === "Enter" && flat[sel]) go(flat[sel].href);
              }}
              className="h-12 flex-1 bg-transparent text-[15px] outline-none placeholder:text-text-3 focus-visible:outline-none" />
            <kbd className="rounded border border-border px-1.5 font-mono text-[10px] text-text-3">Esc</kbd>
          </div>
          <div className="max-h-[60vh] overflow-y-auto p-2">
            {results.teams.length > 0 && <Group title={t("search.teams")}>{results.teams.map((x) => item(`/team/${x.slug}`, <><TeamLogo team={x} size={22} /><span className="font-medium">{x.name}</span></>))}</Group>}
            {results.competitions.length > 0 && <Group title={t("search.competitions")}>{results.competitions.map((x) => item(`/competition/${x.slug}`, <><CompetitionMark cc={x.cc} /><span className="font-medium">{x.name}</span><span className="text-xs text-text-3">{x.country}</span></>))}</Group>}
            {results.matches.length > 0 && <Group title={t("search.matches")}>{results.matches.map((x) => item(`/match/${x.slug}`, <><Calendar className="size-4 text-text-3" /><span className="font-medium">{x.homeName} – {x.awayName}</span><span className="text-xs text-text-3">{new Date(x.kickoff).toLocaleDateString(locale, { day: "numeric", month: "short" })}</span></>))}</Group>}
            {q && flat.length === 0 && <p className="px-3 py-6 text-center text-sm text-text-3">{t("search.empty")}</p>}
            {q && <p className="px-3 pb-2 pt-1 text-xs text-text-3">{t("search.players")} : {t("search.playersNA")}</p>}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
function Group({ title, children }: { title: string; children: ReactNode }) {
  return <div className="mb-1"><div className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wide text-text-3">{title}</div><ul>{children}</ul></div>;
}

/* ───────────── Sidebar (desktop, repliable) ───────────── */
export function Sidebar({ competitions, trending, teams }: {
  competitions: Pick<Competition, "slug" | "name" | "cc">[];
  trending: { slug: string; homeName: string; awayName: string; home: string | null; away: string | null; pHome?: number; pAway?: number }[];
  teams: Record<string, TeamLite>;
}) {
  const { t } = useI18n();
  const fav = useFavorites("teams");
  const path = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  useEffect(() => { try { setCollapsed(localStorage.getItem("sidebar") === "1"); } catch {} }, []);
  const toggle = () => { setCollapsed((c) => { try { localStorage.setItem("sidebar", c ? "0" : "1"); } catch {} return !c; }); };
  const favTeams = fav.items.map((s) => teams[s]).filter(Boolean);
  const link = (href: string, icon: ReactNode, label: ReactNode, extra?: ReactNode) => (
    <Link href={href} title={collapsed ? String(label) : undefined}
      className={cn("group flex items-center gap-2.5 rounded-lg py-1.5 text-[13px] transition-colors", collapsed ? "justify-center px-0" : "px-2.5",
        path === href ? "bg-surface text-text shadow-card" : "text-text-2 hover:bg-surface hover:text-text")}>
      {icon}{!collapsed && <span className="min-w-0 flex-1 truncate">{label}</span>}{!collapsed && extra}
    </Link>
  );
  return (
    <aside className={cn("sticky top-[72px] hidden h-[calc(100vh-88px)] shrink-0 flex-col pb-4 transition-[width] duration-200 lg:flex", collapsed ? "w-14" : "w-60")} aria-label="Accès rapide">
      <div className="scrollbar-thin flex-1 overflow-y-auto overflow-x-hidden pr-1">
        <SideTitle collapsed={collapsed} icon={<Star className="size-3.5" />}>{t("nav.favorites")}</SideTitle>
        {favTeams.length ? favTeams.map((x) => <div key={x.slug}>{link(`/team/${x.slug}`, <TeamLogo team={x} size={20} />, x.name)}</div>)
          : !collapsed && <p className="px-2.5 py-1 text-xs text-text-3">{t("sidebar.noFavorites")}</p>}
        <SideTitle collapsed={collapsed} icon={<Trophy className="size-3.5" />}>{t("sidebar.competitions")}</SideTitle>
        {competitions.map((c) => <div key={c.slug}>{link(`/competition/${c.slug}`, <CompetitionMark cc={c.cc} size={18} />, c.name)}</div>)}
        <SideTitle collapsed={collapsed} icon={<Activity className="size-3.5" />}>{t("sidebar.trending")}</SideTitle>
        {trending.map((m) => (
          <div key={m.slug}>{link(`/match/${m.slug}`, <TeamLogo team={m.home ? teams[m.home] : null} size={18} />, `${m.homeName} – ${m.awayName}`,
            m.pHome != null ? <span className="w-10 shrink-0" title={`1 ${Math.round(m.pHome * 100)} % · 2 ${Math.round((m.pAway ?? 0) * 100)} %`}><ProbabilityBar home={m.pHome} draw={Math.max(0, 1 - m.pHome - (m.pAway ?? 0))} away={m.pAway ?? 0} variant="mini" animate={false} /></span> : null)}</div>
        ))}
      </div>
      <button onClick={toggle} className={cn("mt-2 flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-text-3 hover:bg-surface hover:text-text", collapsed && "justify-center")}
        aria-label={collapsed ? "Déplier la barre latérale" : "Réduire la barre latérale"}>
        {collapsed ? <ChevronsRight className="size-4" /> : <><ChevronsLeft className="size-4" />Réduire</>}
      </button>
    </aside>
  );
}
function SideTitle({ icon, children, collapsed }: { icon: ReactNode; children: ReactNode; collapsed?: boolean }) {
  return collapsed ? <div className="mx-auto my-3 h-px w-6 bg-border first:mt-0" />
    : <div className="mb-1 mt-5 flex items-center gap-1.5 px-2.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-text-3 first:mt-0">{icon}{children}</div>;
}

/* ───────────── BottomNavigation (mobile) ───────────── */
export function MobileNav() {
  const path = usePathname();
  const { t } = useI18n();
  const items = [
    { href: "/", icon: Home, k: "nav.home" as TKey, m: (p: string) => p === "/" },
    { href: "/matches", icon: Calendar, k: "nav.matches" as TKey, m: (p: string) => p.startsWith("/match") },
    { href: "/predictions", icon: BrainCircuit, k: "nav.ai" as TKey, m: (p: string) => p.startsWith("/predictions") || p.startsWith("/ai-performance") },
    { href: "/statistics", icon: BarChart3, k: "nav.stats" as TKey, m: (p: string) => p.startsWith("/statistics") || p.startsWith("/competition") || p.startsWith("/team") || p.startsWith("/standings") },
    { href: "/profile", icon: User, k: "nav.profile" as TKey, m: (p: string) => p.startsWith("/profile") },
  ];
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-surface/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl md:hidden" aria-label="Navigation mobile">
      <div className="grid grid-cols-5">
        {items.map(({ href, icon: I, k, m }) => {
          const on = m(path);
          return (
            <Link key={href} href={href} aria-current={on ? "page" : undefined} className={cn("flex min-h-[56px] flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors", on ? "text-brand" : "text-text-3")}>
              <span className={cn("grid h-7 w-12 place-items-center rounded-full transition-colors", on && "bg-brand-soft")}><I className="size-[19px]" /></span>{t(k)}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
export const BottomNavigation = MobileNav;

/* ───────────── Footer ───────────── */
export function Footer({ meta }: { meta: { generatedAt: string; dataAsOf: string; mode: DataMode; model: string; sources: string[] } }) {
  const { t, locale } = useI18n();
  return (
    <footer className="mt-10 border-t border-border bg-surface">
      <div className="mx-auto grid max-w-[1440px] gap-6 px-4 py-8 text-sm text-text-2 sm:grid-cols-3 lg:px-6">
        <div className="space-y-2">
          <Logo />
          <p className="text-xs leading-relaxed text-text-3">{t("disclaimer")}</p>
        </div>
        <nav className="grid grid-cols-2 gap-1 text-[13px]" aria-label="Pied de page">
          {[["/", "nav.matches"], ["/competitions", "nav.competitions"], ["/predictions", "nav.predictions"], ["/markets", "nav.markets"],
            ["/ai-performance", "nav.performance"], ["/statistics", "nav.stats"], ["/teams", "nav.teams"], ["/standings", "nav.standings"],
            ["/assistant", "nav.assistant"], ["/profile", "nav.profile"]].map(([h, k]) => (
            <Link key={h} href={h} className="text-text-2 hover:text-text">{t(k as TKey)}</Link>
          ))}
        </nav>
        <div className="space-y-1 text-xs text-text-3">
          <p>Modèle {meta.model} · statistique (Elo, pi-ratings, GAS, Poisson–Dixon-Coles)</p>
          <p suppressHydrationWarning>Données historiques au {new Date(meta.dataAsOf).toLocaleDateString(locale)} · publication {new Date(meta.generatedAt).toLocaleString(locale, { dateStyle: "short", timeStyle: "short" })}</p>
          <p>Sources : {meta.sources.length ? meta.sources.join(" · ") : "historique xgabora (football-data.co.uk, ClubElo)"}</p>
          <p><Link href="/ai-performance" className="underline">Transparence du modèle</Link> · <Link href="/assistant" className="underline">assistant</Link></p>
        </div>
      </div>
    </footer>
  );
}

const BANNER: Record<Exclude<DataMode, "live">, { chip: string; text: (d: string, ref: string, src: string) => string }> = {
  fixtures: { chip: "Calendrier", text: (_, __, src) => `Calendrier et résultats réels (${src || "sources publiques"}). Mise à jour toutes les 2 heures, pas de score minute par minute.` },
  offline: { chip: "Hors ligne", text: (d) => `Aucune source de calendrier joignable : affichage des derniers résultats réels connus (données au ${d}).` },
  replay: { chip: "Rejeu", text: (_, ref) => `Journée du ${ref} rejouée : le modèle n'utilise que les données antérieures à cette date. Matchs, scores et cotes sont réels.` },
};

export function ModeBanner({ mode, dataAsOf, referenceDate, freshness, sources = [] }: { mode: DataMode; dataAsOf: string; referenceDate: string; freshness?: Meta["freshness"]; sources?: string[] }) {
  const src = [...new Set(sources.map((x) => x.split(" (")[0]).filter((x) => !x.includes("rejeu")))].join(", ");
  const f = (d: string) => new Date(d).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
  const retard = freshness?.stale && mode !== "replay";
  if (mode === "live" && !retard) return null;
  const b = mode === "live" ? null : BANNER[mode];
  return (
    <div className="border-b border-border bg-surface">
      {b && (
        <p className="mx-auto flex max-w-[1440px] items-center justify-center gap-2 px-4 py-1.5 text-center text-[11px] text-text-2 lg:px-6">
          <span className="shrink-0 rounded bg-brand-soft px-1.5 py-px text-[10px] font-bold uppercase tracking-wide text-brand-ink">{b.chip}</span>{b.text(f(dataAsOf), f(referenceDate), src)}
        </p>
      )}
      {retard && (
        <p className="mx-auto flex max-w-[1440px] items-center justify-center gap-2 bg-warn-soft/50 px-4 py-1.5 text-center text-[11px] text-text-2 lg:px-6">
          <span className="shrink-0 rounded bg-warn-soft px-1.5 py-px text-[10px] font-bold uppercase tracking-wide text-warn">Données en retard</span>
          Résultats connus jusqu&apos;au {f(freshness!.lastResult)}{freshness!.missingResults ? ` · ${freshness!.missingResults} match(s) joué(s) sans score publié` : ""} — certaines prédictions n&apos;intègrent pas encore les derniers résultats.
        </p>
      )}
    </div>
  );
}
