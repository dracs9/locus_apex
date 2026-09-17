import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Achievement, ChancePoint, University } from "@/api/types";
import { t } from "@/i18n/ru";
import { shortDate } from "@/lib/format";
import { useUi } from "@/store/ui";

const LEVEL = { low: 1, medium: 2, high: 3 } as const;
const SERIES_VARS = ["--primary", "--accent", "--safety"];

function cssColor(name: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v ? `hsl(${v})` : "currentColor";
}

/** Step chart of chance labels over time with achievement markers. */
export function ChanceChart({ points, unis, achievements }: { points: ChancePoint[]; unis: Map<string, University>; achievements: Achievement[] }) {
  useUi((s) => s.theme); // re-read CSS colors when the theme changes
  const ids = Object.keys(points[0]?.chance_by_uni ?? {});
  const data = points.map((p) => ({
    date: p.date,
    achievement: p.achievement_id,
    ...Object.fromEntries(ids.map((id) => [id, p.chance_by_uni[id] ? LEVEL[p.chance_by_uni[id]!] : null])),
  }));
  const byId = new Map(achievements.map((a) => [a.id, a]));
  const muted = cssColor("--muted-foreground");
  const grid = cssColor("--border");
  const labels: Record<number, string> = { 1: t.chanceShort.low, 2: t.chanceShort.medium, 3: t.chanceShort.high };

  return (
    <div className="h-64 w-full" role="img" aria-label={t.today.historyTitle}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 12, bottom: 0, left: -8 }}>
          <CartesianGrid stroke={grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="date" tickFormatter={(d: string) => shortDate(d).slice(0, -5)} tick={{ fontSize: 11, fill: muted }} stroke={grid} minTickGap={16} />
          <YAxis domain={[0.5, 3.5]} ticks={[1, 2, 3]} tickFormatter={(v: number) => labels[v] ?? ""} tick={{ fontSize: 11, fill: muted }} stroke={grid} width={72} />
          <Tooltip
            formatter={(v: number, name: string) => [labels[v] ?? "не рекомендован", unis.get(name)?.name ?? name]}
            labelFormatter={(d: string, payload) => {
              const aid = payload?.[0]?.payload?.achievement as string | null;
              const a = aid ? byId.get(aid) : undefined;
              const what = a ? ` — ${a.title ?? t.achievements.types[a.type]}${a.score != null ? ` ${a.score}` : ""}` : "";
              return `${shortDate(d)}${what}`;
            }}
            contentStyle={{ borderRadius: 12, fontSize: 12, background: cssColor("--card"), borderColor: grid }}
          />
          {data
            .filter((d) => d.achievement)
            .map((d) => (
              <ReferenceLine key={d.date} x={d.date} stroke={cssColor("--accent")} strokeDasharray="2 4" />
            ))}
          {ids.map((id, i) => (
            <Line
              key={id}
              type="stepAfter"
              dataKey={id}
              name={id}
              stroke={cssColor(SERIES_VARS[i % SERIES_VARS.length])}
              strokeWidth={2.5}
              dot={{ r: 4 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          ))}
          <Legend formatter={(id: string) => <span className="text-xs text-foreground">{unis.get(id)?.name ?? id}</span>} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
