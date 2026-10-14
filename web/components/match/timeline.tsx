"use client";
/* MatchStatsCard : statistiques réelles d'un match terminé (tirs, corners, cartons, fautes), source football-data.co.uk. */
import { BarChart3 } from "lucide-react";
import type { Match } from "@/lib/types";
import { CompareBar } from "./team-comparison";
import { Card, CardHeader } from "../ui/primitives";

const ROWS: [keyof NonNullable<Match["stats"]>, string, "high" | "low"][] = [
  ["shots", "Tirs", "high"], ["shotsOnTarget", "Tirs cadrés", "high"], ["corners", "Corners", "high"],
  ["fouls", "Fautes", "low"], ["yellow", "Cartons jaunes", "low"], ["red", "Cartons rouges", "low"],
];

export function MatchStatsCard({ m }: { m: Match }) {
  const s = m.stats;
  if (!s) return null;
  const rows = ROWS.filter(([k]) => s[k]?.home != null && s[k]?.away != null);
  if (!rows.length) return null;
  return (
    <Card>
      <CardHeader title="Statistiques du match" subtitle={m.halftime ? `Mi-temps ${m.halftime.home}–${m.halftime.away}` : "Match terminé"}
        icon={<BarChart3 className="size-4 text-brand" />} />
      <div className="divide-y divide-border/60 px-4 pb-3">
        {rows.map(([k, label, better]) => (
          <CompareBar key={k} row={{ label, home: s[k].home as number, away: s[k].away as number, fmt: (v) => String(v), better }} />
        ))}
      </div>
    </Card>
  );
}
