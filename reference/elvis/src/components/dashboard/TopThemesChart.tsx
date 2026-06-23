import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import type { ThemeData, Sentiment } from "@/lib/types";

const sentimentColor: Record<Sentiment, string> = {
  positive: "hsl(var(--sentiment-positive))",
  neutral: "hsl(var(--sentiment-neutral))",
  negative: "hsl(var(--sentiment-negative))",
  mixed: "hsl(var(--sentiment-mixed))",
};

export function TopThemesChart({ data }: { data: ThemeData[] }) {
  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <h3 className="text-sm font-semibold mb-4">Top Themes</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
            <XAxis type="number" tick={{ fontSize: 10 }} />
            <YAxis dataKey="name" type="category" width={130} tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
            />
            <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={20}>
              {data.map((entry, index) => (
                <Cell key={index} fill={sentimentColor[entry.sentiment]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
