import { fetchResults } from "@/lib/storage"
import { PerformanceChart } from "@/components/performance-chart"
import { ResultCards } from "@/components/result-cards"
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
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Training Results</h1>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          Backtest performance from the latest model training. These show how each model performed on historical data — not live predictions.
          For today's buy/sell signals, see the <a href="/signals" className="text-blue-500 hover:underline">Signals</a> page.
        </p>
      </div>

      {usResults.length > 0 && (
        <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-6">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">US — Top Returns</h2>
          <PerformanceChart data={usResults} names={names} />
        </div>
      )}

      {krxResults.length > 0 && (
        <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-6">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4">KRX — Top Returns</h2>
          <PerformanceChart data={krxResults} names={names} />
        </div>
      )}

      <ResultCards results={usResults} title="US Market" names={names} />
      <ResultCards results={krxResults} title="KRX Market" names={names} />
    </div>
  )
}
