/* Scores en direct : proxy serveur vers football-data.org (la clé API ne quitte jamais le serveur).
   Réponse : { mode, updatedAt, matches: { "fd-<id>": { status, minute, score } } } — mise en cache 30 s. */
import { NextResponse } from "next/server";
import type { LiveState, MatchStatus } from "@/lib/types";

export const dynamic = "force-dynamic";
const STATUS: Record<string, MatchStatus> = {
  SCHEDULED: "scheduled", TIMED: "scheduled", IN_PLAY: "live", PAUSED: "halftime", FINISHED: "finished", AWARDED: "finished",
  POSTPONED: "postponed", SUSPENDED: "postponed", CANCELLED: "cancelled",
};

export async function GET() {
  const key = process.env.FOOTBALL_DATA_API_KEY;
  if (!key) return NextResponse.json({ mode: "off", updatedAt: new Date().toISOString(), matches: {} });
  const day = (d: number) => new Date(Date.now() + d * 864e5).toISOString().slice(0, 10);
  try {
    const r = await fetch(`https://api.football-data.org/v4/matches?competitions=PL,PD,SA,BL1,FL1,CL&dateFrom=${day(-1)}&dateTo=${day(1)}`, {
      headers: { "X-Auth-Token": key }, next: { revalidate: 30 },
    });
    if (!r.ok) return NextResponse.json({ error: `football-data ${r.status}` }, { status: 502 });
    const j = await r.json();
    const matches: Record<string, LiveState> = {};
    for (const m of j.matches ?? []) {
      const ft = m.score?.fullTime ?? {};
      matches[`fd-${m.id}`] = { status: STATUS[m.status] ?? "scheduled", minute: m.minute ?? null, score: ft.home != null ? { home: ft.home, away: ft.away } : null };
    }
    return NextResponse.json({ mode: "live", updatedAt: new Date().toISOString(), matches }, { headers: { "Cache-Control": "s-maxage=30, stale-while-revalidate=60" } });
  } catch {
    return NextResponse.json({ error: "API indisponible" }, { status: 503 });
  }
}
