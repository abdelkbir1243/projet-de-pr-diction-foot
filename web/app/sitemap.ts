import type { MetadataRoute } from "next";
import { getCompetitions, getMatches, getMeta, getTeams } from "@/lib/data";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "https://goalgebra.vercel.app";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date(getMeta().generatedAt);
  const page = (path: string, priority: number, freq: MetadataRoute.Sitemap[number]["changeFrequency"] = "daily") => ({ url: `${SITE}${path}`, lastModified: now, changeFrequency: freq, priority });
  return [
    page("/", 1, "hourly"), page("/matches", 0.9, "hourly"), page("/predictions", 0.9, "hourly"), page("/competitions", 0.7), page("/standings", 0.7),
    page("/statistics", 0.6), page("/teams", 0.6), page("/ai-performance", 0.7), page("/markets", 0.8, "hourly"), page("/assistant", 0.5, "monthly"),
    ...getCompetitions().map((c) => page(`/competition/${c.slug}`, 0.7)),
    ...getTeams().map((t) => page(`/team/${t.slug}`, 0.6, "weekly")),
    ...getMatches().map((m) => page(`/match/${m.slug}`, 0.8, "hourly")),
  ];
}
