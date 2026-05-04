import { supabase } from "@/lib/supabase"
import { getTickerNames } from "@/lib/ticker-names"
import { getLatestRate } from "@/lib/currency"
import { Signal } from "lucide-react"
import { PortfolioOverview } from "@/components/portfolio-overview"

export default async function Home() {
  const { data: portfolios } = await supabase
    .from("portfolios")
    .select("id, name, created_at")

  const { data: recentSignals } = await supabase
    .from("signals")
    .select("ticker, signal, probability, created_at")
    .order("created_at", { ascending: false })
    .limit(10)

  // Fetch holdings for each portfolio (for total value calc)
  const portfolioSummaries = await Promise.all(
    (portfolios || []).map(async (p) => {
      const { data: holdings } = await supabase
        .from("holdings")
        .select("shares, current_price, avg_cost, currency")
        .eq("portfolio_id", p.id)
      return { ...p, holdings: holdings || [] }
    })
  )

  const signalTickers = recentSignals?.map((s) => s.ticker) || []
  const names = await getTickerNames(signalTickers)
  const rate = await getLatestRate()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Overview</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PortfolioOverview portfolios={portfolioSummaries} rate={rate} />

        {/* Recent Signals Card */}
        <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-6 border border-gray-200 dark:border-[#1F1F23]">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Signal className="w-4 h-4" />
            Recent Signals
          </h2>
          {recentSignals?.length ? (
            <div className="space-y-2">
              {recentSignals.map((s, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-[#1F1F23] transition-colors">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">{names[s.ticker] || s.ticker}</span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      s.signal === 1 ? "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400"
                      : s.signal === -1 ? "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                    }`}>
                      {s.signal === 1 ? "BUY" : s.signal === -1 ? "SELL" : "HOLD"}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {(s.probability * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">No signals yet.</p>
          )}
        </div>
      </div>
    </div>
  )
}
