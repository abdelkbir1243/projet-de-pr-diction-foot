"use client";
import type { Team } from "@/lib/types";
import { LineChart, RadarCompare } from "./charts";

export function EloChart({ team }: { team: Team }) {
  const data = team.eloHistory.map((p) => ({ x: new Date(p.date).toLocaleDateString("fr-FR", { month: "short", year: "2-digit" }), elo: p.elo }));
  return <LineChart data={data} lines={[{ key: "elo", name: "Elo", color: "var(--brand)" }]} height={220} />;
}

export function TeamRadar({ team }: { team: Team }) {
  const r = team.radar;
  const data = [
    { axis: "Attaque", home: r.attack, away: 50 }, { axis: "Défense", home: r.defense, away: 50 }, { axis: "Forme", home: r.form, away: 50 },
    { axis: "Contrôle", home: r.control, away: 50 }, { axis: "Finition", home: r.finishing, away: 50 }, { axis: "À domicile", home: r.venueHome, away: 50 },
    { axis: "À l'extérieur", home: r.venueAway, away: 50 },
  ];
  return <RadarCompare data={data} homeName={team.name} awayName="Médiane de la ligue" height={300} />;
}
