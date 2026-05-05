"use client"

import { useState } from "react"
import { BarChart2, TrendingUp, TrendingDown, ChevronDown, ChevronRight } from "lucide-react"

export function ResultCards({ results, title, names }: { results: any[]; title: string; names: Record<string, string> }) {
  const [open, setOpen] = useState(false)

  if (!results.length) return null

  return (
    <div className="space-y-4">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 text-lg font-bold text-gray-900 dark:text-white hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
      >
        {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        <BarChart2 className="w-4 h-4" />
        {title}
        <span className="text-sm font-normal text-gray-500 dark:text-gray-400">({results.length} tickers)</span>
      </button>

      {open && (
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
      )}
    </div>
  )
}
