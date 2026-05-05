import { fetchResults } from "@/lib/storage"
import { BarChart2, TrendingUp, TrendingDown } from "lucide-react"
import { PerformanceChart } from "@/components/performance-chart"
import { getTickerNames } from "@/lib/ticker-names"

async function getResults(market: string) {
  const filename = market === "us" ? "training_results.csv" : `training_results_${market}.csv`
  const csv = await fetchResults(filename)
  if (!csv) return []
  const lines = csv.trim().split("\n")
  const headers = lines[0].split(",")
  return lines.slice(1).map((line) => {
    const values = line.split(",")
    const row: Record<string, any> = {}
    headers.forEach((h, i) => { row[h] = isNaN(Number(values[i])) ? values[i] : Number(values[i]) })
    return row
  })
}

function ResultCards({ results, title, names }: { results: any[]; title: string; names: Record<string, string> }) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <BarChart2 className="w-4 h-4" />
        {title}
        <span className="text-sm font-normal text-gray-500 dark:text-gray-400">({results.length} tickers)</span>
      </h2>

      {results.length ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {results.map((r, i) => (
            <div key={i} className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-4 space-y-3 hover:border-gray-300 dark:hover:border-[#2F2F33] transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{names[r.ticker] || r.ticker}</h3>
                  {names[r.ticker] && <p className="text-xs text-gray-500 dark:text-gray-400">{r.ticker}</p>}
                </div>
                {r.total_return > 0
                  ? <TrendingUp className="w-4 h-4 text-emerald-500" />
                  : <TrendingDown className="w-4 h-4 text-red-500" />}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Return</p>
                  <p className={`text-sm font-medium ${r.total_return > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
                    {(r.total_return * 100).toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Sharpe</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{r.sharpe_ratio?.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Win Rate</p>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">{(r.win_rate * 100).toFixed(0)}%</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Max DD</p>
                  <p className="text-sm font-medium text-red-600 dark:text-red-400">{(r.max_drawdown * 100).toFixed(1)}%</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">No results available. Configure OCI_RESULTS_URL.</p>
      )}
    </div>
  )
}

export default async function TrainingPage() {
  const usResults = await getResults("us")
  const krxResults = await getResults("krx")

  const allTickers = [...usResults, ...krxResults].map((r) => {
    const t = String(r.ticker)
    return /^\d+$/.test(t) ? t.padStart(6, "0") : t
  })
  const names = await getTickerNames(allTickers)

  // Also normalize ticker in results for display lookup
  for (const r of [...usResults, ...krxResults]) {
    const t = String(r.ticker)
    if (/^\d+$/.test(t)) r.ticker = t.padStart(6, "0")
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Training Results</h1>

      {usResults.length > 0 && (
        <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-6">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">US — Top Returns</h2>
          <PerformanceChart data={usResults} />
        </div>
      )}

      {krxResults.length > 0 && (
        <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-6">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">KRX — Top Returns</h2>
          <PerformanceChart data={krxResults} />
        </div>
      )}

      <ResultCards results={usResults} title="US Market" names={names} />
      <ResultCards results={krxResults} title="KRX Market" names={names} />
    </div>
  )
}
