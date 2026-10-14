"use client";
import Link from "next/link";
import { useTheme } from "next-themes";
import { Star } from "lucide-react";
import type { MatchSummary, TeamLite } from "@/lib/types";
import { useFavorites } from "@/lib/favorites";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { TeamLogo } from "./football";
import { Card, CardHeader, EmptyState } from "./ui/primitives";

export function ProfileView({ teams, matches }: { teams: Record<string, TeamLite>; matches: MatchSummary[] }) {
  const ft = useFavorites("teams"), fm = useFavorites("matches");
  const { theme, setTheme } = useTheme();
  const { locale } = useI18n();
  const favMatches = matches.filter((m) => fm.has(m.id) || (m.home && ft.has(m.home)) || (m.away && ft.has(m.away)));
  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="min-w-0 space-y-4">
        <Card>
          <CardHeader title="Équipes favorites" icon={<Star className="size-4 text-warn" />} />
          {ft.items.length ? (
            <ul className="grid gap-2 p-4 sm:grid-cols-2">
              {ft.items.map((s) => teams[s] && (
                <li key={s} className="flex items-center gap-2 rounded-lg border border-border p-2.5 transition-colors hover:border-border-strong">
                  <TeamLogo team={teams[s]} size={24} /><Link href={`/team/${s}`} className="flex-1 truncate text-sm font-medium hover:underline">{teams[s].name}</Link>
                  <button onClick={() => ft.toggle(s)} className="text-xs text-text-3 hover:text-bad">Retirer</button>
                </li>
              ))}
            </ul>
          ) : <EmptyState icon={<Star className="size-5" />} title="Aucune équipe favorite" hint="Ouvrez la page d'une équipe et cliquez sur l'étoile." />}
        </Card>
        <Card>
          <CardHeader title="Matchs suivis" subtitle="Matchs favoris et matchs de vos équipes" />
          {favMatches.length ? (
            <ul className="divide-y divide-border">
              {favMatches.map((m) => (
                <li key={m.id}><Link href={`/match/${m.slug}`} className="flex items-center gap-3 px-4 py-2.5 text-[13px] hover:bg-surface-2">
                  <span className="w-24 shrink-0 text-xs text-text-3 sm:w-28" suppressHydrationWarning>{new Date(m.kickoff).toLocaleString(locale, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
                  <TeamLogo team={m.home ? teams[m.home] : null} size={18} /><span className="flex-1 truncate">{m.homeName} – {m.awayName}</span>
                </Link></li>
              ))}
            </ul>
          ) : <EmptyState title="Aucun match suivi" hint="Ajoutez des matchs avec l'étoile du Match Center." />}
        </Card>
      </div>
      <Card>
        <CardHeader title="Préférences" />
        <div className="space-y-4 p-4 text-[13px]">
          <Pref label="Thème">{(["light", "dark", "system"] as const).map((t) => <Opt key={t} on={theme === t} onClick={() => setTheme(t)}>{t === "light" ? "Clair" : t === "dark" ? "Sombre" : "Système"}</Opt>)}</Pref>
          <p className="rounded-lg bg-surface-2 p-3 text-xs text-text-2">Vos favoris sont enregistrés dans ce navigateur. Aucun compte n'est nécessaire : rien n'est envoyé à un serveur.</p>
        </div>
      </Card>
    </div>
  );
}
const Pref = ({ label, children }: { label: string; children: React.ReactNode }) => <div><div className="mb-1.5 text-xs font-medium text-text-3">{label}</div><div className="flex gap-1 rounded-lg bg-surface-2 p-1">{children}</div></div>;
const Opt = ({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) => (
  <button onClick={onClick} className={cn("flex-1 rounded-md py-1.5 font-medium transition-colors", on ? "bg-surface text-brand-ink shadow-card" : "text-text-3 hover:text-text")}>{children}</button>
);
