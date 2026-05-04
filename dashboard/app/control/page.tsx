"use client"

import { useState, useEffect } from "react"
import { Power } from "lucide-react"

export default function ControlPage() {
  const [enabled, setEnabled] = useState<boolean | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetch("/api/settings").then((r) => r.json()).then((s) => {
      setEnabled(s.trading_enabled === "true")
    })
  }, [])

  async function toggle() {
    setSaving(true)
    const newValue = !enabled
    await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: "trading_enabled", value: String(newValue) }),
    })
    setEnabled(newValue)
    setSaving(false)
  }

  if (enabled === null) return <div className="text-gray-500 dark:text-gray-400">Loading...</div>

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Control Panel</h1>

      <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-6">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Power className="w-4 h-4" />
          Trading Status
        </h2>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
          Global kill switch. When paused, trade.py will not execute any trades across all portfolios.
        </p>
        <div className="flex items-center gap-4">
          <button
            onClick={toggle}
            disabled={saving}
            className={`px-6 py-2.5 rounded-lg text-sm font-medium text-white transition-colors ${
              enabled ? "bg-red-600 hover:bg-red-700" : "bg-emerald-600 hover:bg-emerald-700"
            } disabled:opacity-50`}
          >
            {enabled ? "⏸ Pause Trading" : "▶ Resume Trading"}
          </button>
          <span className={`text-sm font-medium ${enabled ? "text-emerald-500" : "text-red-500"}`}>
            ● {enabled ? "Active" : "Paused"}
          </span>
        </div>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-4">
          Strategy parameters (threshold, position size, VIX limit) are now configured per-portfolio on the Portfolio page.
        </p>
      </div>
    </div>
  )
}
