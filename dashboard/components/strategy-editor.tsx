"use client"

import { useState } from "react"
import { Settings } from "lucide-react"

interface StrategyParams {
  signal_threshold: number
  vix_threshold: number
  max_position_pct: number
  min_cash_pct: number
}

export function StrategyEditor({ portfolioId, params }: { portfolioId: number; params: StrategyParams }) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(params)
  const [saving, setSaving] = useState(false)

  async function save() {
    setSaving(true)
    await fetch("/api/portfolio/strategy", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ portfolio_id: portfolioId, ...form }),
    })
    setSaving(false)
    setOpen(false)
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors">
        <Settings className="w-3 h-3" />
        Strategy: threshold {params.signal_threshold}, VIX {params.vix_threshold}
      </button>
    )
  }

  return (
    <div className="mt-3 p-3 rounded-lg border border-gray-200 dark:border-[#1F1F23] space-y-3">
      <h4 className="text-xs font-semibold text-gray-900 dark:text-white flex items-center gap-1">
        <Settings className="w-3 h-3" /> Strategy Parameters
      </h4>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Signal Threshold" desc="Buy above this confidence (0.1–0.9)" value={form.signal_threshold} min={0.1} max={0.9} step={0.05} onChange={(v) => setForm({ ...form, signal_threshold: v })} />
        <Field label="VIX Threshold" desc="Reduce buys above this VIX (15–50)" value={form.vix_threshold} min={15} max={50} step={1} onChange={(v) => setForm({ ...form, vix_threshold: v })} />
        <Field label="Max Position %" desc="Max weight per ticker (0.05–1.0)" value={form.max_position_pct} min={0.05} max={1.0} step={0.05} onChange={(v) => setForm({ ...form, max_position_pct: v })} />
        <Field label="Min Cash %" desc="Keep this much cash (0–0.9)" value={form.min_cash_pct} min={0} max={0.9} step={0.05} onChange={(v) => setForm({ ...form, min_cash_pct: v })} />
      </div>
      {(form.min_cash_pct >= 0.9 || form.signal_threshold > 0.8 || form.max_position_pct <= 0.05) && (
        <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 rounded-md">
          ⚠️ {form.min_cash_pct >= 0.9 ? "Min cash ≥90% will block almost all buys. " : ""}
          {form.signal_threshold > 0.8 ? "Threshold >0.8 means very few signals pass. " : ""}
          {form.max_position_pct <= 0.05 ? "Max position ≤5% heavily penalizes existing holdings. " : ""}
        </p>
      )}
      <div className="flex gap-2">
        <button onClick={save} disabled={saving} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">{saving ? "..." : "Save"}</button>
        <button onClick={() => { setOpen(false); setForm(params) }} className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700">Cancel</button>
      </div>
    </div>
  )
}

function Field({ label, desc, value, min, max, step, onChange }: { label: string; desc: string; value: number; min?: number; max?: number; step?: number; onChange: (v: number) => void }) {
  return (
    <div>
      <label className="text-xs font-medium text-gray-900 dark:text-white">{label}</label>
      <p className="text-[10px] text-gray-400 mb-1">{desc}</p>
      <input
        type="number"
        step={step || "any"}
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full px-2 py-1.5 text-xs rounded-md border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white"
      />
    </div>
  )
}
