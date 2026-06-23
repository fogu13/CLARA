import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import type { TeamRouting, TargetTeam } from "@/lib/types";

const teamColor: Record<TargetTeam, string> = {
  marketing: "hsl(var(--team-marketing))",
  product: "hsl(var(--team-product))",
  cx: "hsl(var(--team-cx))",
  sales: "hsl(var(--team-sales))",
  engineering: "hsl(var(--team-engineering))",
};

export function TeamRoutingPie({ data }: { data: TeamRouting[] }) {
  const total = data.reduce((s, d) => s + d.count, 0);

  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <h3 className="text-sm font-semibold mb-4">Team Routing</h3>
      <div className="h-64 relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="count" nameKey="team" cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3}>
              {data.map((entry) => (
                <Cell key={entry.team} fill={teamColor[entry.team]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
              formatter={(value: number, name: string) => [value, name === "cx" ? "CX" : name.charAt(0).toUpperCase() + name.slice(1)]}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <div className="text-2xl font-bold">{total}</div>
            <div className="text-[10px] text-muted-foreground">open</div>
          </div>
        </div>
      </div>
      <div className="flex flex-wrap gap-3 mt-2 justify-center">
        {data.map((d) => (
          <div key={d.team} className="flex items-center gap-1.5 text-xs">
            <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: teamColor[d.team] }} />
            <span className="text-muted-foreground capitalize">{d.team === "cx" ? "CX" : d.team}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
