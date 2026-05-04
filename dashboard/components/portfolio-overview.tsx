"use client"

import { useState } from "react"
import { Wallet } from "lucide-react"
import { CurrencyToggle } from "./currency-toggle"
import { convert, formatCurrency, type Currency } from "@/lib/currency"

interface PortfolioSummary {
  id: number
  name: string
  created_at: string
  holdings: { shares: number; current_price: number | null; avg_cost: number; currency: string }[]
}

export function PortfolioOverview({ portfolios, rate }: { portfolios: PortfolioSummary[]; rate: number }) {
  const [baseCurrency, setBaseCurrency] = useState<Currency>("USD")

  function totalValue(holdings: PortfolioSummary["holdings"]): number {
    return holdings.reduce((sum, h) => {
      const val = h.shares * (h.current_price || h.avg_cost)
      return sum + convert(val, (h.currency || "USD") as Currency, baseCurrency, rate)
    }, 0)
  }

  return (
    <div className="bg-white dark:bg-[#0F0F12] rounded-xl p-6 border border-gray-200 dark:border-[#1F1F23]">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Wallet className="w-4 h-4" /> Portfolios
        </h2>
        <CurrencyToggle defaultCurrency={baseCurrency} onChange={setBaseCurrency} />
      </div>
      {portfolios.length ? (
        <div className="space-y-2">
          {portfolios.map((p) => (
            <div key={p.id} className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-[#1F1F23] transition-colors">
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">{p.name}</h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">{new Date(p.created_at).toLocaleDateString()}</p>
              </div>
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                {formatCurrency(totalValue(p.holdings), baseCurrency)}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">No portfolios yet.</p>
      )}
    </div>
  )
}
