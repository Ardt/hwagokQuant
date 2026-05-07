"use client"

import { useState } from "react"
import { ChevronDown, ChevronRight, Pencil } from "lucide-react"
import { CURRENCY_SYMBOLS, type Currency } from "@/lib/currency"

interface Holding {
  id: number
  ticker: string
  shares: number
  avg_cost: number
  current_price: number
  currency: string
}

interface Transaction {
  id: number
  ticker: string
  action: string
  shares: number
  price: number
  total: number
  timestamp: string
}

export function HoldingsTable({ holdings, transactions, portfolioId, names }: {
  holdings: Holding[]
  transactions: Transaction[]
  portfolioId: number
  names: Record<string, string>
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [editing, setEditing] = useState(false)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [edits, setEdits] = useState<Record<number, { shares: string; price: string }>>({})
  const [submitting, setSubmitting] = useState(false)

  function toggleExpand(ticker: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(ticker) ? next.delete(ticker) : next.add(ticker)
      return next
    })
  }

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
    if (!edits[id]) {
      const h = holdings.find((h) => h.id === id)!
      setEdits((prev) => ({ ...prev, [id]: { shares: String(h.shares), price: String(h.avg_cost) } }))
    }
  }

  function updateEdit(id: number, field: "shares" | "price", value: string) {
    setEdits((prev) => ({ ...prev, [id]: { ...prev[id], [field]: value } }))
  }

  async function handleSubmit() {
    setSubmitting(true)
    for (const id of Array.from(selected)) {
      const h = holdings.find((h) => h.id === id)!
      const edit = edits[id]
      const newShares = Number(edit.shares)
      const newPrice = Number(edit.price)
      if (newShares === h.shares && newPrice === h.avg_cost) continue
      const shareDiff = newShares - h.shares
      await fetch("/api/trade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          portfolio_id: portfolioId,
          action: "ADJUST",
          ticker: h.ticker,
          shares: shareDiff,
          price: newPrice,
        }),
      })
    }
    setSubmitting(false)
    setEditing(false)
    setSelected(new Set())
    setEdits({})
    window.location.reload()
  }

  if (!holdings.length) return <p className="text-sm text-gray-500 dark:text-gray-400">No holdings.</p>

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white">Holdings</h3>
        <button
          onClick={() => { setEditing(!editing); setSelected(new Set()); setEdits({}) }}
          className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
        >
          <Pencil className="w-3 h-3" /> {editing ? "Cancel" : "Adjust"}
        </button>
      </div>

      {holdings.map((h) => {
        const cur = (h.currency || (/^\d{6}$/.test(h.ticker) ? "KRW" : "USD")) as Currency
        const sym = CURRENCY_SYMBOLS[cur]
        const tickerTxns = transactions.filter((t) => t.ticker === h.ticker)
        const isExpanded = expanded.has(h.ticker)

        return (
          <div key={h.id} className="rounded-lg border border-gray-100 dark:border-[#1F1F23]">
            <div className="flex items-center gap-2 p-3 hover:bg-gray-50 dark:hover:bg-[#1F1F23] transition-colors">
              {editing && (
                <input
                  type="checkbox"
                  checked={selected.has(h.id)}
                  onChange={() => toggleSelect(h.id)}
                  className="w-4 h-4 rounded border-gray-300 dark:border-gray-600"
                />
              )}
              <button onClick={() => toggleExpand(h.ticker)} className="flex items-center text-gray-500 dark:text-gray-400">
                {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              </button>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{names[h.ticker] || h.ticker}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {names[h.ticker] ? h.ticker + " · " : ""}{h.shares} shares @ {sym}{Number(h.avg_cost).toLocaleString()}
                </p>
              </div>
              {editing && selected.has(h.id) ? (
                <div className="flex items-center gap-2">
                  <input type="number" value={edits[h.id]?.shares ?? h.shares} onChange={(e) => updateEdit(h.id, "shares", e.target.value)} className="w-20 px-2 py-1 text-xs rounded border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white" />
                  <input type="number" step="any" value={edits[h.id]?.price ?? h.avg_cost} onChange={(e) => updateEdit(h.id, "price", e.target.value)} className="w-24 px-2 py-1 text-xs rounded border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white" />
                </div>
              ) : (
                <div className="text-right">
                  <span className="text-sm font-medium text-gray-900 dark:text-white">{sym}{Number(h.current_price || h.avg_cost).toLocaleString()}</span>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{sym}{(h.shares * (h.current_price || h.avg_cost)).toLocaleString()}</p>
                </div>
              )}
            </div>

            {isExpanded && tickerTxns.length > 0 && (
              <div className="px-4 pb-3 border-t border-gray-100 dark:border-[#1F1F23]">
                <div className="pt-2 space-y-1">
                  {tickerTxns.map((t) => (
                    <div key={t.id} className="flex items-center justify-between text-xs py-1">
                      <div className="flex items-center gap-2">
                        <span className={`font-medium px-1.5 py-0.5 rounded ${
                          t.action === "BUY" || t.action === "TRANSFER_IN" || t.action === "ADJUST"
                            ? "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400"
                            : "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400"
                        }`}>{t.action}</span>
                        <span className="text-gray-500 dark:text-gray-400">{t.shares} @ {sym}{Number(t.price).toLocaleString()}</span>
                      </div>
                      <span className="text-gray-400 dark:text-gray-500">{new Date(t.timestamp).toLocaleDateString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {isExpanded && tickerTxns.length === 0 && (
              <div className="px-4 pb-3 border-t border-gray-100 dark:border-[#1F1F23]">
                <p className="pt-2 text-xs text-gray-400 dark:text-gray-500">No transactions recorded.</p>
              </div>
            )}
          </div>
        )
      })}

      {editing && selected.size > 0 && (
        <button onClick={handleSubmit} disabled={submitting} className="w-full px-4 py-2 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">
          {submitting ? "Saving..." : `Adjust ${selected.size} holding${selected.size > 1 ? "s" : ""}`}
        </button>
      )}
    </div>
  )
}
