"use client"

import { useState, useEffect, useRef } from "react"
import { Plus } from "lucide-react"

export function TradeForm({ portfolios }: { portfolios: { id: number; name: string }[] }) {
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ portfolio_id: "", action: "BUY", ticker: "", shares: "", price: "" })
  const [suggestions, setSuggestions] = useState<{ ticker: string; name: string }[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  function handleTickerChange(value: string) {
    setForm({ ...form, ticker: value })
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (value.length < 1) { setSuggestions([]); return }
    debounceRef.current = setTimeout(async () => {
      const res = await fetch(`/api/tickers?q=${encodeURIComponent(value)}&limit=5`)
      const data = await res.json()
      setSuggestions(data)
      setShowSuggestions(data.length > 0)
    }, 300)
  }

  function selectTicker(ticker: string) {
    setForm({ ...form, ticker })
    setShowSuggestions(false)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    await fetch("/api/trade", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        portfolio_id: Number(form.portfolio_id),
        action: form.action,
        ticker: form.ticker.toUpperCase(),
        shares: Number(form.shares),
        price: Number(form.price),
      }),
    })
    setSubmitting(false)
    setOpen(false)
    setForm({ portfolio_id: form.portfolio_id, action: "BUY", ticker: "", shares: "", price: "" })
    window.location.reload()
  }

  const total = Number(form.shares) * Number(form.price)

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors">
        <Plus className="w-4 h-4" /> Record Trade
      </button>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-4 space-y-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Record Trade</h3>
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <select value={form.portfolio_id} onChange={(e) => setForm({ ...form, portfolio_id: e.target.value })} required className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white">
          <option value="">Portfolio</option>
          {portfolios.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select value={form.action} onChange={(e) => setForm({ ...form, action: e.target.value })} className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white">
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
          <option value="TRANSFER_IN">TRANSFER IN</option>
          <option value="TRANSFER_OUT">TRANSFER OUT</option>
          <option value="ADJUST">ADJUST</option>
          <option value="DEPOSIT">DEPOSIT</option>
          <option value="WITHDRAW">WITHDRAW</option>
        </select>
        {(form.action === "DEPOSIT" || form.action === "WITHDRAW") ? (
          <>
            <select value={form.ticker} onChange={(e) => setForm({ ...form, ticker: e.target.value })} required className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white">
              <option value="">Currency</option>
              <option value="USD">USD</option>
              <option value="KRW">KRW</option>
            </select>
            <input placeholder="Amount" type="number" step="any" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} required className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white sm:col-span-2" />
          </>
        ) : form.action === "EXCHANGE" ? (
          <>
            <select value={form.ticker} onChange={(e) => setForm({ ...form, ticker: e.target.value })} required className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white">
              <option value="">From</option>
              <option value="USD">USD → KRW</option>
              <option value="KRW">KRW → USD</option>
            </select>
            <input placeholder="Amount" type="number" step="any" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} required className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white" />
            <input placeholder="Rate (e.g. 1400)" type="number" step="any" value={form.shares} onChange={(e) => setForm({ ...form, shares: e.target.value })} required className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white" />
          </>
        ) : (
          <>
        <div className="relative">
          <input placeholder="Ticker or name" value={form.ticker} onChange={(e) => handleTickerChange(e.target.value)} onFocus={() => suggestions.length && setShowSuggestions(true)} onBlur={() => setTimeout(() => setShowSuggestions(false), 200)} required className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white" />
          {showSuggestions && (
            <div className="absolute z-10 top-full mt-1 w-full bg-white dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#1F1F23] rounded-lg shadow-lg overflow-hidden">
              {suggestions.map((s) => (
                <button key={s.ticker} type="button" onMouseDown={() => selectTicker(s.ticker)} className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-[#1F1F23] flex justify-between">
                  <span className="text-gray-900 dark:text-white">{s.name}</span>
                  <span className="text-gray-400 dark:text-gray-500">{s.ticker}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <input placeholder="Shares" type="number" value={form.shares} onChange={(e) => setForm({ ...form, shares: e.target.value })} required className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white" />
        <input placeholder="Price" type="number" step="any" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} required className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white" />
          </>
        )}
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {total > 0 && `Total: ${total.toLocaleString()}`}
        </span>
        <div className="flex gap-2">
          <button type="button" onClick={() => setOpen(false)} className="px-3 py-2 text-xs rounded-lg border border-gray-200 dark:border-[#1F1F23] text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-[#1F1F23]">Cancel</button>
          <button type="submit" disabled={submitting} className="px-4 py-2 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">{submitting ? "..." : "Submit"}</button>
        </div>
      </div>
    </form>
  )
}
