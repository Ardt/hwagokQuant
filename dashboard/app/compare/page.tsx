import { createSupabaseServer } from "@/lib/supabase-server"
import { computeSharpe, computeMaxDrawdown } from "@/lib/analytics"
import { BarChart2 } from "lucide-react"

export default async function ComparePage() {
  const supabase = await createSupabaseServer()
  const { data: portfolios } = await supabase.from("portfolios").select("*")

  if (!portfolios?.length) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Compare Portfolios</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">No portfolios to compare.</p>
      </div>
    )
  }

  const comparisons = await Promise.all(
    portfolios.map(async (p) => {
      const { data: holdings } = await supabase.from("holdings").select("*").eq("portfolio_id", p.id)
      const { data: snapshots } = await supabase
        .from("portfolio_snapshots").select("total_value, timestamp")
        .eq("portfolio_id", p.id).order("timestamp", { ascending: true })

      const totalValue = (holdings || []).reduce((s, h) => s + h.shares * (h.current_price || h.avg_cost), 0)
      const sharpe = computeSharpe(snapshots || [])
      const maxDd = computeMaxDrawdown(snapshots || [])
      const totalReturn = snapshots?.length
        ? (snapshots[snapshots.length - 1].total_value - snapshots[0].total_value) / snapshots[0].total_value
        : 0

      return {
        id: p.id,
        name: p.name,
        initial_capital: p.initial_capital,
        total_value: totalValue,
        total_return: totalReturn,
        sharpe,
        max_drawdown: maxDd,
        num_holdings: holdings?.length || 0,
      }
    })
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <BarChart2 className="w-5 h-5" /> Compare Portfolios
      </h1>

      <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 dark:border-[#1F1F23] text-xs text-gray-500 dark:text-gray-400">
              <th className="text-left p-3 font-medium">Portfolio</th>
              <th className="text-right p-3 font-medium">Holdings</th>
              <th className="text-right p-3 font-medium">Value</th>
              <th className="text-right p-3 font-medium">Return</th>
              <th className="text-right p-3 font-medium">Sharpe</th>
              <th className="text-right p-3 font-medium">Max DD</th>
            </tr>
          </thead>
          <tbody>
            {comparisons.map((c) => (
              <tr key={c.id} className="border-b border-gray-50 dark:border-[#1F1F23] hover:bg-gray-50 dark:hover:bg-[#1F1F23]">
                <td className="p-3 font-medium text-gray-900 dark:text-white">{c.name}</td>
                <td className="p-3 text-right text-gray-600 dark:text-gray-400">{c.num_holdings}</td>
                <td className="p-3 text-right text-gray-900 dark:text-white">{c.total_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                <td className={`p-3 text-right font-medium ${c.total_return >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
                  {(c.total_return * 100).toFixed(1)}%
                </td>
                <td className={`p-3 text-right ${c.sharpe >= 1 ? "text-emerald-600 dark:text-emerald-400" : "text-gray-900 dark:text-white"}`}>
                  {c.sharpe.toFixed(2)}
                </td>
                <td className="p-3 text-right text-red-600 dark:text-red-400">
                  {(c.max_drawdown * 100).toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
