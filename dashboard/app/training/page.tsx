import { fetchResults } from "@/lib/storage"
import { PerformanceChart } from "@/components/performance-chart"
import { ResultCards } from "@/components/result-cards"
import { getTickerNames } from "@/lib/ticker-names"

const MODELS = ["lstm_60", "lstm_30"]

async function getResults(market: string, modelName: string) {
  const suffix = market === "us" ? "" : `_${market}`
  const filename = `training_results${suffix}_${modelName}.csv`
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
  const resultsByModel: Record<string, { us: any[]; krx: any[] }> = {}
  for (const model of MODELS) {
    resultsByModel[model] = {
      us: await getResults("us", model),
      krx: await getResults("krx", model),
    }
  }

  const allTickers = Object.values(resultsByModel).flatMap((r) =>
    [...r.us, ...r.krx].map((row) => {
      const t = String(row.ticker)
      return /^\d+$/.test(t) ? t.padStart(6, "0") : t
    })
  )
  const names = await getTickerNames(allTickers)

  // Normalize tickers for display
  for (const model of MODELS) {
    for (const r of [...resultsByModel[model].us, ...resultsByModel[model].krx]) {
      const t = String(r.ticker)
      if (/^\d+$/.test(t)) r.ticker = t.padStart(6, "0")
    }
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

      {MODELS.map((model) => {
        const { us, krx } = resultsByModel[model]
        if (!us.length && !krx.length) return null
        return (
          <div key={model} className="space-y-4">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white border-b border-gray-200 dark:border-[#1F1F23] pb-2">
              Model: {model.replace("_", " ").toUpperCase()}
            </h2>

            {us.length > 0 && (
              <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-6">
                <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-4">US — Top Returns</h3>
                <PerformanceChart data={us} names={names} />
              </div>
            )}

            {krx.length > 0 && (
              <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-6">
                <h3 className="text-sm font-bold text-gray-900 dark:text-white mb-4">KRX — Top Returns</h3>
                <PerformanceChart data={krx} names={names} />
              </div>
            )}

            <ResultCards results={us} title="US Market" names={names} />
            <ResultCards results={krx} title="KRX Market" names={names} />
          </div>
        )
      })}
    </div>
  )
}
