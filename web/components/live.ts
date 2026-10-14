"use client";
import { createContext, useContext, useEffect, useState } from "react";
import type { LiveState } from "@/lib/types";

/** Horloge figée (mode rejeu) : toute l'interface se place à la date rejouée. */
export const ClockContext = createContext<number | null>(null);

/** Horloge partagée (statut des matchs, minute de jeu). */
export function useNow(intervalMs = 30_000) {
  const fixed = useContext(ClockContext);
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    if (fixed) { setNow(fixed); return; }
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, fixed]);
  return now;
}

/** Scores en direct depuis /api/live (proxy serveur de football-data.org). Sans clé API, renvoie {}. */
export function useLiveFeed(enabled: boolean, intervalMs = 60_000) {
  const [feed, setFeed] = useState<Record<string, LiveState>>({});
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!enabled) return;
    let stop = false;
    const tick = async () => {
      try {
        const r = await fetch("/api/live", { cache: "no-store" });
        if (!r.ok) throw new Error(String(r.status));
        const j = await r.json();
        if (!stop) { setFeed(j.matches ?? {}); setError(false); }
      } catch {
        if (!stop) setError(true);
      }
    };
    tick();
    const id = setInterval(tick, intervalMs);
    return () => { stop = true; clearInterval(id); };
  }, [enabled, intervalMs]);
  return { feed, error };
}
