"use client";
/* Graphiques (Recharts) : RadarChart, LineChart, Donut, calibration. Couleurs = tokens CSS, lisibles en clair comme en sombre. */
import {
  CartesianGrid, Cell, Legend, Line, LineChart as RLineChart, Pie, PieChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart as RRadarChart,
  ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from "recharts";
import { useEffect, useState } from "react";

const tip = {
  contentStyle: { background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, fontSize: 12, boxShadow: "var(--shadow-lg)", color: "var(--text)" },
  labelStyle: { color: "var(--text-2)", fontWeight: 600 },
  itemStyle: { color: "var(--text)" },
};
const axis = { stroke: "var(--text-3)", fontSize: 11, tickLine: false, axisLine: false } as const;

/** Évite le rendu côté serveur (ResponsiveContainer mesure le DOM). */
function useMounted() { const [m, setM] = useState(false); useEffect(() => setM(true), []); return m; }
function Frame({ height, children }: { height: number; children: React.ReactElement }) {
  const mounted = useMounted();
  return <div style={{ height }} className="w-full">{mounted ? <ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer> : <div className="skeleton h-full w-full" />}</div>;
}

export function RadarCompare({ data, homeName, awayName, height = 300 }: { data: { axis: string; home: number; away: number }[]; homeName: string; awayName: string; height?: number }) {
  return (
    <Frame height={height}>
      <RRadarChart data={data} outerRadius="78%" margin={{ top: 8, right: 24, bottom: 8, left: 24 }}>
        <PolarGrid stroke="var(--border-strong)" />
        <PolarAngleAxis dataKey="axis" tick={{ fill: "var(--text-2)", fontSize: 11 }} />
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        <Radar name={homeName} dataKey="home" stroke="var(--home)" fill="var(--home)" fillOpacity={0.18} strokeWidth={2} dot={{ r: 3 }} />
        <Radar name={awayName} dataKey="away" stroke="var(--away)" fill="var(--away)" fillOpacity={0.14} strokeWidth={2} dot={{ r: 3 }} />
        <Tooltip {...tip} formatter={(v) => [`${v} / 100`]} />
        <Legend wrapperStyle={{ fontSize: 12, color: "var(--text-2)" }} iconType="circle" iconSize={8} />
      </RRadarChart>
    </Frame>
  );
}

export function LineChart({ data, lines, height = 220, yDomain, yFormat, xKey = "x" }: {
  data: Record<string, number | string | null>[]; lines: { key: string; name: string; color: string; dashed?: boolean }[]; height?: number;
  yDomain?: [number | "auto", number | "auto"]; yFormat?: (v: number) => string; xKey?: string;
}) {
  return (
    <Frame height={height}>
      <RLineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
        <CartesianGrid stroke="var(--border)" vertical={false} />
        <XAxis dataKey={xKey} {...axis} minTickGap={24} />
        <YAxis {...axis} domain={yDomain ?? ["auto", "auto"]} tickFormatter={yFormat} width={48} />
        <Tooltip {...tip} formatter={(v) => (typeof v === "number" && yFormat ? yFormat(v) : String(v ?? "—"))} />
        {lines.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} iconType="plainline" />}
        {lines.map((l) => (
          <Line key={l.key} type="monotone" dataKey={l.key} name={l.name} stroke={l.color} strokeWidth={2} strokeDasharray={l.dashed ? "5 4" : undefined}
            dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--surface)" }} connectNulls />
        ))}
      </RLineChart>
    </Frame>
  );
}

export function Donut({ values, height = 160, center, tooltip = false }: { values: { name: string; value: number; color: string }[]; height?: number; center?: React.ReactNode; tooltip?: boolean }) {
  return (
    <div className="relative" style={{ height }}>
      <Frame height={height}>
        <PieChart>
          <Pie data={values} dataKey="value" nameKey="name" innerRadius="74%" outerRadius="100%" paddingAngle={2} cornerRadius={4} animationDuration={700} stroke="var(--surface)" strokeWidth={2} startAngle={90} endAngle={-270}>
            {values.map((v) => <Cell key={v.name} fill={v.color} />)}
          </Pie>
          {tooltip && <Tooltip {...tip} formatter={(v) => `${Math.round(Number(v) * 100)} %`} />}
        </PieChart>
      </Frame>
      {center && <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">{center}</div>}
    </div>
  );
}

export function CalibrationChart({ points, market, height = 280 }: { points: { predicted: number; observed: number; n: number }[]; market?: { predicted: number; observed: number }[]; height?: number }) {
  const d = points.map((p) => ({ x: +(p.predicted * 100).toFixed(1), y: +(p.observed * 100).toFixed(1), n: p.n }));
  return (
    <Frame height={height}>
      <ScatterChart margin={{ top: 8, right: 12, bottom: 16, left: -4 }}>
        <CartesianGrid stroke="var(--border)" />
        <XAxis type="number" dataKey="x" name="Probabilité annoncée" unit=" %" domain={[0, 80]} {...axis} label={{ value: "Probabilité annoncée", position: "insideBottom", offset: -8, fill: "var(--text-3)", fontSize: 11 }} />
        <YAxis type="number" dataKey="y" name="Fréquence observée" unit=" %" domain={[0, 80]} {...axis} />
        <ZAxis dataKey="n" range={[60, 60]} name="Prédictions" />
        <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 80, y: 80 }]} stroke="var(--text-3)" strokeDasharray="4 4" />
        <Tooltip {...tip} cursor={{ strokeDasharray: "3 3" }} />
        <Scatter name="Modèle" data={d} fill="var(--home)" line={{ stroke: "var(--home)", strokeWidth: 2 }} shape="circle" />
        {market && <Scatter name="Cotes" data={market.map((p) => ({ x: p.predicted * 100, y: p.observed * 100 }))} fill="var(--draw)" />}
      </ScatterChart>
    </Frame>
  );
}
