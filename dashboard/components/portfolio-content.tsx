"use client"

import { useState } from "react"
import { Briefcase, TrendingUp, ArrowRightLeft, ChevronDown, ChevronRight } from "lucide-react"
import { CurrencyToggle } from "./currency-toggle"
import { convert, formatCurrency, CURRENCY_SYMBOLS, type Currency } from "@/lib/currency"
import { EquityChart } from "./equity-chart"
import { Watchlist } from "./watchlist"
import { DeletePortfolio } from "./portfolio-manage"
import { StrategyEditor } from "./strategy-editor"

interface PortfolioData {
  id: number
  name: string
  initial_capital: number
  base_currency: string
  signal_threshold: number | null
  vix_threshold: number | null
  max_position_pct: number | null
  min_cash_pct: number | null
  allocator_strategy: string | null
  holdings: any[]
  snapshots: any[]
  transactions: any[]
  allTransactions: any[]
  watchlist: { ticker: string }[]
  sharpe: number
  maxDrawdown: number
  realizedPnl: { ticker: string; shares: number; sell_price: number; cost_basis: number; pnl: number; timestamp: string }[]
}

export function PortfolioContent({ portfolios, names, rate }: {
  portfolios: PortfolioData[]
  names: Record<string, string>
  rate: number
}) {
  const [baseCurrency, setBaseCurrency] = useState<Currency>("USD")

  function totalValue(holdings: any[]): number {
    return holdings.reduce((sum, h) => {
      const val = h.shares * (h.current_price || h.avg_cost)
      return sum + convert(val, h.currency || "USD", baseCurrency, rate)
    }, 0)
  }

  const [openIds, setOpenIds] = useState<Set<number>>(new Set())
  function toggle(id: number) {
    setOpenIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  return (
    <>
      {portfolios.map((p) => (
        <div key={p.id} className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23]">
          <div className="p-4 border-b border-gray-100 dark:border-[#1F1F23] flex items-center justify-between">
            <div>
              <button onClick={() => toggle(p.id)} className="flex items-center gap-2 text-lg font-bold text-gray-900 dark:text-white hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
                {openIds.has(p.id) ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                <Briefcase className="w-4 h-4" /> {p.name}
                <DeletePortfolio id={p.id} name={p.name} />
              </button>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Holdings: {formatCurrency(totalValue(p.holdings), baseCurrency)} | {(() => {
                  const cash: Record<string, number> = { USD: 0, KRW: 0 }
                  for (const t of p.allTransactions) {
                    const isCash = t.ticker?.startsWith("CASH_")
                    const cur = isCash ? t.ticker.replace("CASH_", "") : (/^\d{6}$/.test(t.ticker) ? "KRW" : "USD")
                    if (t.action === "DEPOSIT" || (t.action === "EXCHANGE" && isCash)) cash[cur] += t.total
                    else if (t.action === "WITHDRAW") cash[cur] -= t.total
                    else if (t.action === "BUY") cash[cur] -= t.total
                    else if (t.action === "SELL") cash[cur] += t.total
                  }
                  return Object.entries(cash).filter(([,v]) => v !== 0).map(([c, v]) => `${c}: ${c === "KRW" ? "₩" : "$"}${Math.round(v).toLocaleString()}`).join(" | ") || "Cash: $0"
                })()} 
              </p>
              <StrategyEditor portfolioId={p.id} params={{
                signal_threshold: p.signal_threshold ?? 0.5,
                vix_threshold: p.vix_threshold ?? 30,
                max_position_pct: p.max_position_pct ?? 0.25,
                min_cash_pct: p.min_cash_pct ?? 0.10,
                allocator_strategy: p.allocator_strategy ?? "equal_weight",
              }} />
            </div>
            <CurrencyToggle defaultCurrency={baseCurrency} onChange={setBaseCurrency} />
          </div>

          {openIds.has(p.id) && <>
          {/* Risk Metrics */}
          {(p.sharpe !== 0 || p.maxDrawdown !== 0) && (
            <div className="p-4 border-b border-gray-100 dark:border-[#1F1F23] flex gap-6">
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Sharpe Ratio</p>
                <p className={`text-sm font-semibold ${p.sharpe >= 1 ? "text-emerald-600 dark:text-emerald-400" : p.sharpe >= 0 ? "text-gray-900 dark:text-white" : "text-red-600 dark:text-red-400"}`}>
                  {p.sharpe.toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">Max Drawdown</p>
                <p className="text-sm font-semibold text-red-600 dark:text-red-400">
                  {(p.maxDrawdown * 100).toFixed(1)}%
                </p>
              </div>
              {p.realizedPnl.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Realized P&L</p>
                  <p className={`text-sm font-semibold ${p.realizedPnl.reduce((s, r) => s + r.pnl, 0) >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
                    {p.realizedPnl.reduce((s, r) => s + r.pnl, 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Equity Curve */}
          {p.snapshots.length > 1 && (
            <div className="p-4 border-b border-gray-100 dark:border-[#1F1F23]">
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                <TrendingUp className="w-3.5 h-3.5" /> Equity Curve
              </h3>
              <EquityChart snapshots={p.snapshots} />
            </div>
          )}

          {/* Holdings — native currency */}
          <div className="p-4 border-b border-gray-100 dark:border-[#1F1F23]">
            {(() => {
              // Calculate cash per currency
              const cashByCur: Record<string, number> = {}
              for (const t of p.allTransactions) {
                const isCash = t.ticker?.startsWith("CASH_")
                const cur = isCash ? t.ticker.replace("CASH_", "") : (/^\d{6}$/.test(t.ticker) ? "KRW" : "USD")
                if (t.action === "DEPOSIT" || (t.action === "EXCHANGE" && isCash)) cashByCur[cur] = (cashByCur[cur] || 0) + t.total
                else if (t.action === "WITHDRAW") cashByCur[cur] = (cashByCur[cur] || 0) - t.total
                else if (t.action === "BUY") cashByCur[cur] = (cashByCur[cur] || 0) - t.total
                else if (t.action === "SELL") cashByCur[cur] = (cashByCur[cur] || 0) + t.total
              }
              const cashRows = Object.entries(cashByCur).filter(([,v]) => v !== 0)
              const hasContent = p.holdings.length > 0 || cashRows.length > 0

              return hasContent ? (
                <div className="space-y-1">
                  {/* Cash rows */}
                  {cashRows.map(([cur, amount]) => (
                    <div key={`cash-${cur}`} className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-[#1A1A1E]">
                      <div>
                        <h3 className="text-sm font-medium text-gray-900 dark:text-white">{cur}</h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Cash</p>
                      </div>
                      <div className="text-right">
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {cur === "KRW" ? "₩" : "$"}{Math.round(amount).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  ))}
                  {/* Stock holdings */}
                  {p.holdings.map((h: any) => {
                    const cur = (h.currency || (/^\d{6}$/.test(h.ticker) ? "KRW" : "USD")) as Currency
                    const sym = CURRENCY_SYMBOLS[cur]
                    const val = h.shares * (h.current_price || h.avg_cost)
                    return (
                      <div key={h.id} className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-[#1F1F23] transition-colors">
                        <div>
                          <h3 className="text-sm font-medium text-gray-900 dark:text-white">{names[h.ticker] || h.ticker}</h3>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {names[h.ticker] ? h.ticker + " · " : ""}{h.shares} shares @ {sym}{Number(h.avg_cost).toLocaleString()}
                          </p>
                        </div>
                        <div className="text-right">
                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                            {sym}{Number(h.current_price || h.avg_cost).toLocaleString()}
                          </span>
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {formatCurrency(val, cur)}
                          </p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">No holdings.</p>
              )
            })()}
          </div>

          {/* Watchlist */}
          <div className="p-4 border-b border-gray-100 dark:border-[#1F1F23]">
            <Watchlist portfolioId={p.id} items={p.watchlist} names={names} />
          </div>


          {/* Transactions */}
          {p.transactions.length > 0 && (
            <div className="p-4">
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                <ArrowRightLeft className="w-3.5 h-3.5" /> Recent Transactions
              </h3>
              <div className="space-y-1">
                {p.transactions.map((t: any) => (
                  <div key={t.id} className="flex items-center justify-between p-2 rounded-lg text-xs">
                    <div className="flex items-center gap-3">
                      <span className={`font-medium px-2 py-0.5 rounded ${
                        t.action === "BUY" ? "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400"
                        : "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400"
                      }`}>{t.action}</span>
                      <span className="text-gray-900 dark:text-white font-medium">{names[t.ticker] || t.ticker}</span>
                      <span className="text-gray-500 dark:text-gray-400">{t.shares} @ {Number(t.price).toLocaleString()}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {t.source && <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 uppercase">{t.source}</span>}
                      <span className="text-gray-400 dark:text-gray-500">{new Date(t.timestamp).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          </>}
        </div>
      ))}
    </>
  )
}
