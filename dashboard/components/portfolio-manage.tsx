"use client"

import { useState } from "react"
import { Plus, Trash2 } from "lucide-react"

export function CreatePortfolio() {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ name: "", initial_capital: "100000", base_currency: "USD" })
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    await fetch("/api/portfolio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: form.name, initial_capital: Number(form.initial_capital), base_currency: form.base_currency }),
    })
    setSubmitting(false)
    setOpen(false)
    window.location.reload()
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-[#1F1F23] text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-[#1F1F23]">
        <Plus className="w-3 h-3" /> New
      </button>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="px-2 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white w-24" />
      <input placeholder="Capital" type="number" value={form.initial_capital} onChange={(e) => setForm({ ...form, initial_capital: e.target.value })} className="px-2 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white w-24" />
      <select value={form.base_currency} onChange={(e) => setForm({ ...form, base_currency: e.target.value })} className="px-2 py-1.5 text-xs rounded-lg border border-gray-200 dark:border-[#1F1F23] bg-gray-50 dark:bg-[#1A1A1E] text-gray-900 dark:text-white">
        <option value="USD">USD</option>
        <option value="KRW">KRW</option>
      </select>
      <button type="submit" disabled={submitting} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50">Create</button>
      <button type="button" onClick={() => setOpen(false)} className="px-2 py-1.5 text-xs text-gray-400 hover:text-gray-600">Cancel</button>
    </form>
  )
}

export function DeletePortfolio({ id, name }: { id: number; name: string }) {
  const [confirming, setConfirming] = useState(false)
  const [input, setInput] = useState("")

  async function handleDelete() {
    if (input !== name) return
    await fetch("/api/portfolio", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    })
    window.location.reload()
  }

  if (!confirming) {
    return (
      <button onClick={() => setConfirming(true)} className="p-1 text-gray-400 hover:text-red-500 transition-colors" title="Delete portfolio">
        <Trash2 className="w-3.5 h-3.5" />
      </button>
    )
  }

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-red-500">Type "{name}" to confirm:</span>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={name}
        className="px-2 py-1 rounded border border-red-300 dark:border-red-800 bg-red-50 dark:bg-red-900/20 text-gray-900 dark:text-white text-xs w-28"
      />
      <button onClick={handleDelete} disabled={input !== name} className="px-2 py-1 rounded bg-red-600 text-white disabled:opacity-30">Delete</button>
      <button onClick={() => { setConfirming(false); setInput("") }} className="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400">Cancel</button>
    </div>
  )
}
