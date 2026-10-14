import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Footer, MobileNav, ModeBanner, Navbar, Sidebar, type SearchIndex } from "@/components/chrome";
import { AssistantProvider } from "@/components/assistant";
import { getCompetitions, getMatches, getMeta, getTeams, teamLite } from "@/lib/data";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "https://goalgebra.vercel.app";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: { default: "Goalgebra — Football Analytics & prédictions IA", template: "%s · Goalgebra" },
  description: "Matchs du jour, statistiques d'équipes, classements et probabilités calculées par un modèle statistique transparent (Elo, pi-ratings, Poisson–Dixon-Coles).",
  applicationName: "Goalgebra",
  openGraph: { type: "website", siteName: "Goalgebra", locale: "fr_FR" },
  twitter: { card: "summary_large_image" },
  alternates: { canonical: "/" },
};
export const viewport: Viewport = {
  themeColor: [{ media: "(prefers-color-scheme: light)", color: "#ffffff" }, { media: "(prefers-color-scheme: dark)", color: "#111723" }],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const meta = getMeta();
  const comps = getCompetitions();
  const teams = getTeams();
  const matches = getMatches();
  const index: SearchIndex = {
    teams: Object.values(teamLite()),
    competitions: comps.map(({ slug, name, cc, country }) => ({ slug, name, cc, country })),
    matches: matches.map(({ slug, homeName, awayName, kickoff, competition, home, away }) => ({ slug, homeName, awayName, kickoff, competition, home, away })),
  };
  const upcoming = matches.filter((m) => m.prediction && m.status === "scheduled");
  const trending = upcoming
    .map((m) => ({ m, score: 1 - Math.abs((m.prediction!.home - m.prediction!.away)) + ((teams.find((t) => t.slug === m.home)?.elo ?? 1500) + (teams.find((t) => t.slug === m.away)?.elo ?? 1500)) / 4000 }))
    .sort((a, b) => b.score - a.score).slice(0, 5)
    .map(({ m }) => ({ slug: m.slug, homeName: m.homeName, awayName: m.awayName, home: m.home, away: m.away, pHome: m.prediction!.home, pAway: m.prediction!.away }));
  return (
    <html lang="fr" suppressHydrationWarning className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="min-h-screen font-sans">
        <Providers fixedNow={meta.now}>
          <AssistantProvider>
          <a href="#contenu" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2">Aller au contenu</a>
          <Navbar index={index} />
          <ModeBanner mode={meta.mode} dataAsOf={meta.dataAsOf} referenceDate={meta.referenceDate} freshness={meta.freshness} sources={meta.sources} />
          <div className="mx-auto flex max-w-[1440px] gap-5 px-3 pb-24 pt-4 sm:px-4 md:pb-8 lg:gap-6 lg:px-6">
            <Sidebar competitions={comps.map(({ slug, name, cc }) => ({ slug, name, cc }))} trending={trending} teams={teamLite()} />
            <main id="contenu" className="min-w-0 flex-1">{children}</main>
          </div>
          <Footer meta={meta} />
          <MobileNav />
          </AssistantProvider>
        </Providers>
      </body>
    </html>
  );
}
