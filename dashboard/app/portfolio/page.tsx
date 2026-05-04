import { supabase } from "@/lib/supabase"
import { Briefcase, TrendingUp } from "lucide-react"
import { EquityChart } from "@/components/equity-chart"

export default async function PortfolioPage() {
  const { data: portfolios } = await supabase.from("portfolios").select("*")

  if (!portfolios?.length) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Portfolio</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">No portfolios.</p>
      </div>
    )
  }

  const details = await Promise.all(
    portfolios.map(async (p) => {
      const { data: holdings } = await supabase.from("holdings").select("*").eq("portfolio_id", p.id)
      const { data: snapshots } = await supabase
        .from("portfolio_snapshots")
        .select("timestamp, total_value")
        .eq("portfolio_id", p.id)
        .order("timestamp", { ascending: true })
      return { ...p, holdings: holdings || [], snapshots: snapshots || [] }
    })
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Portfolio</h1>

      {details.map((p) => (
        <div key={p.id} className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23]">
          <div className="p-4 border-b border-gray-100 dark:border-[#1F1F23]">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Briefcase className="w-4 h-4" />
              {p.name}
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Capital: {p.initial_capital?.toLocaleString()}
            </p>
          </div>

          {/* Equity Curve */}
          {p.snapshots.length > 1 && (
            <div className="p-4 border-b border-gray-100 dark:border-[#1F1F23]">
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                <TrendingUp className="w-3.5 h-3.5" />
                Equity Curve
              </h3>
              <EquityChart snapshots={p.snapshots} />
            </div>
          )}

          {/* Holdings */}
          <div className="p-4">
            {p.holdings.length ? (
              <div className="space-y-1">
                {p.holdings.map((h: any) => (
                  <div key={h.id} className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-[#1F1F23] transition-colors">
                    <div>
                      <h3 className="text-sm font-medium text-gray-900 dark:text-white">{h.ticker}</h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{h.shares} shares @ {h.avg_cost?.toFixed(2)}</p>
                    </div>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {h.current_price ? `$${h.current_price.toFixed(2)}` : "—"}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400">No holdings.</p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
