"use client"

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts"

export function PerformanceChart({ data }: { data: any[] }) {
  const sorted = [...data].sort((a, b) => b.total_return - a.total_return).slice(0, 20)
  const chartData = sorted.map((d) => ({
    ticker: d.ticker,
    return: +(d.total_return * 100).toFixed(1),
  }))

  return (
    <div className="w-full h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <XAxis dataKey="ticker" tick={{ fontSize: 11, fill: "#888" }} />
          <YAxis tick={{ fontSize: 11, fill: "#888" }} tickFormatter={(v) => `${v}%`} />
          <Tooltip
            contentStyle={{ background: "#1a1a1e", border: "1px solid #333", borderRadius: 8 }}
            labelStyle={{ color: "#fff" }}
            formatter={(value: number) => [`${value}%`, "Return"]}
          />
          <Bar dataKey="return" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.return >= 0 ? "#10b981" : "#ef4444"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
