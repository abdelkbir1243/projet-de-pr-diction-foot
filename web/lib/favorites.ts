"use client";
import { useCallback, useEffect, useState } from "react";

/** Favoris (équipes et matchs) conservés dans le navigateur. Avec un compte utilisateur, ils seront synchronisés côté serveur. */
type Kind = "teams" | "matches";
const KEY = (k: Kind) => `fav:${k}`;
const EVT = "favorites-change";

function read(kind: Kind): string[] {
  try { return JSON.parse(localStorage.getItem(KEY(kind)) || "[]"); } catch { return []; }
}

export function useFavorites(kind: Kind) {
  const [items, setItems] = useState<string[]>([]);
  useEffect(() => {
    setItems(read(kind));
    const on = () => setItems(read(kind));
    window.addEventListener(EVT, on); window.addEventListener("storage", on);
    return () => { window.removeEventListener(EVT, on); window.removeEventListener("storage", on); };
  }, [kind]);
  const toggle = useCallback((id: string) => {
    const cur = read(kind);
    const next = cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id];
    try { localStorage.setItem(KEY(kind), JSON.stringify(next)); } catch {}
    window.dispatchEvent(new Event(EVT));
  }, [kind]);
  return { items, has: (id: string) => items.includes(id), toggle };
}
