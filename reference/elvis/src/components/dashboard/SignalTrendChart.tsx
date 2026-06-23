import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { SignalTrendPoint } from "@/lib/types";

export function SignalTrendChart({ data }: { data: SignalTrendPoint[] }) {
  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <h3 className="text-sm font-semibold mb-4">Signal Trend (30d)</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v) => v.slice(5)} className="text-muted-foreground" />
            <YAxis tick={{ fontSize: 10 }} className="text-muted-foreground" />
            <Tooltip
              contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
            />
            <Legend iconSize={8} wrapperStyle={{ fontSize: "12px" }} />
            <Line type="monotone" dataKey="qualitative" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} name="Qualitative" />
            <Line type="monotone" dataKey="quantitative" stroke="hsl(var(--sentiment-mixed))" strokeWidth={2} dot={false} name="Quantitative" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
