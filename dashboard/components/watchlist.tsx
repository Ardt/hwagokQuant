"use client"

import { useState, useRef } from "react"
import { Plus, X, Eye } from "lucide-react"
import { WATCHLIST_MAX_PER_MARKET } from "@/lib/constants"

interface WatchlistProps {
  portfolioId: number
  items: { ticker: string }[]
  names: Record<string, string>
}

function detectMarket(ticker: string): string {
  return /^\d{6}$/.test(ticker) ? "KRX" : "US"
}

export function Watchlist({ portfolioId, items, names }: WatchlistProps) {
  const [list, setList] = useState(items)
  const usCount = list.filter((i) => detectMarket(i.ticker) === "US").length
  const krxCount = list.filter((i) => detectMarket(i.ticker) === "KRX").length
  const [input, setInput] = useState("")
  const [suggestions, setSuggestions] = useState<{ ticker: string; name: string }[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  function handleInput(value: string) {
    setInput(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (value.length < 1) { setSuggestions([]); return }
    debounceRef.current = setTimeout(async () => {
      const res = await fetch(`/api/tickers?q=${encodeURIComponent(value)}&limit=5`)
      const data = await res.json()
      setSuggestions(data)
      setShowSuggestions(data.length > 0)
    }, 300)
  }

  async function addTicker(ticker: string) {
    await fetch("/api/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ portfolio_id: portfolioId, ticker }),
    })
    setList([...list, { ticker }])
    setInput("")
    setShowSuggestions(false)
  }

  async function removeTicker(ticker: string) {
    await fetch("/api/watchlist", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ portfolio_id: portfolioId, ticker }),
    })
    setList(list.filter((i) => i.ticker !== ticker))
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-2">
        <Eye className="w-3.5 h-3.5" /> Watchlist
        <span className="text-xs text-gray-400">US {usCount}/{WATCHLIST_MAX_PER_MARKET} · KRX {krxCount}/{WATCHLIST_MAX_PER_MARKET}</span>
      </h3>

      {/* Ticker chips */}
      <div className="flex flex-wrap gap-2">
        {list.map((item) => (
          <span key={item.ticker} className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-gray-100 dark:bg-[#1F1F23] text-xs text-gray-900 dark:text-white">
            {names[item.ticker] || item.ticker}
            <button onClick={() => removeTicker(item.ticker)} className="text-gray-400 hover:text-red-500">
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
      </div>

      {/* Add input */}
      {(usCount < WATCHLIST_MAX_PER_MARKET || krxCount < WATCHLIST_MAX_PER_MARKET) && (
      <div className="relative w-48">
        <div className="flex gap-1">
          <input
            placeholder="Add ticker..."
            value={input}
            onChange={(e) => handleInput(e.target.value)}
            onFocus={() => suggestions.length && setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            onKeyDown={(e) => { if (e.key === "Enter" && input) { addTicker(input.toUpperCase()); e.preventDefault() } }}
            className="flex-1 px-2 py-1 text-xs rounded-md border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white"
          />
          <button onClick={() => input && addTicker(input.toUpperCase())} className="p-1 rounded-md bg-gray-900 dark:bg-white text-white dark:text-gray-900">
            <Plus className="w-3 h-3" />
          </button>
        </div>
        {showSuggestions && (
          <div className="absolute z-10 top-full mt-1 w-full bg-white dark:bg-[#1A1A1E] border border-gray-200 dark:border-[#1F1F23] rounded-lg shadow-lg overflow-hidden">
            {suggestions.map((s) => (
              <button key={s.ticker} type="button" onMouseDown={() => addTicker(s.ticker)} className="w-full px-2 py-1.5 text-left text-xs hover:bg-gray-50 dark:hover:bg-[#1F1F23] flex justify-between">
                <span className="text-gray-900 dark:text-white">{s.name}</span>
                <span className="text-gray-400">{s.ticker}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      )}
    </div>
  )
}
