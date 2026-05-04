"use client"

import { useState, useEffect } from "react"
import { Settings, Power } from "lucide-react"

interface Settings {
  trading_enabled: string
  signal_threshold: string
  stop_loss: string
  take_profit: string
  max_position_pct: string
  vix_threshold: string
}

export default function ControlPage() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [saving, setSaving] = useState<string | null>(null)

  useEffect(() => {
    fetch("/api/settings").then((r) => r.json()).then(setSettings)
  }, [])

  async function update(key: string, value: string) {
    setSaving(key)
    await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value }),
    })
    setSettings((s) => (s ? { ...s, [key]: value } : s))
    setSaving(null)
  }

  if (!settings) return <div className="text-gray-500 dark:text-gray-400">Loading...</div>

  const tradingEnabled = settings.trading_enabled === "true"

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Control Panel</h1>

      {/* Trading Toggle */}
      <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-6">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Power className="w-4 h-4" />
          Trading Status
        </h2>
        <div className="flex items-center gap-4">
          <button
            onClick={() => update("trading_enabled", tradingEnabled ? "false" : "true")}
            disabled={saving === "trading_enabled"}
            className={`px-6 py-2.5 rounded-lg text-sm font-medium text-white transition-colors ${
              tradingEnabled
                ? "bg-red-600 hover:bg-red-700"
                : "bg-emerald-600 hover:bg-emerald-700"
            } disabled:opacity-50`}
          >
            {tradingEnabled ? "⏸ Pause Trading" : "▶ Resume Trading"}
          </button>
          <span className={`text-sm font-medium ${tradingEnabled ? "text-emerald-500" : "text-red-500"}`}>
            ● {tradingEnabled ? "Active" : "Paused"}
          </span>
        </div>
      </div>

      {/* Strategy Parameters */}
      <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-6">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Settings className="w-4 h-4" />
          Strategy Parameters
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 max-w-2xl">
          <SettingInput label="Signal Threshold" desc="Probability cutoff (0.0–1.0)" value={settings.signal_threshold} onSave={(v) => update("signal_threshold", v)} saving={saving === "signal_threshold"} />
          <SettingInput label="Stop Loss" desc="Max loss before sell (e.g. -0.05)" value={settings.stop_loss} onSave={(v) => update("stop_loss", v)} saving={saving === "stop_loss"} />
          <SettingInput label="Take Profit" desc="Target gain (e.g. 0.10)" value={settings.take_profit} onSave={(v) => update("take_profit", v)} saving={saving === "take_profit"} />
          <SettingInput label="Max Position %" desc="Max weight per ticker (e.g. 0.25)" value={settings.max_position_pct} onSave={(v) => update("max_position_pct", v)} saving={saving === "max_position_pct"} />
          <SettingInput label="VIX Threshold" desc="Suppress BUY above this VIX" value={settings.vix_threshold} onSave={(v) => update("vix_threshold", v)} saving={saving === "vix_threshold"} />
        </div>
      </div>
    </div>
  )
}

function SettingInput({ label, desc, value, onSave, saving }: {
  label: string; desc: string; value: string; onSave: (v: string) => void; saving: boolean
}) {
  const [v, setV] = useState(value)
  const changed = v !== value

  return (
    <div>
      <label className="text-sm font-medium text-gray-900 dark:text-white">{label}</label>
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{desc}</p>
      <div className="flex gap-2">
        <input
          type="text"
          value={v}
          onChange={(e) => setV(e.target.value)}
          className="px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white w-28 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {changed && (
          <button
            onClick={() => onSave(v)}
            disabled={saving}
            className="px-3 py-2 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? "..." : "Save"}
          </button>
        )}
      </div>
    </div>
  )
}
