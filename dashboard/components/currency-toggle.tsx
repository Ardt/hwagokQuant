"use client"

import { useState } from "react"
import type { Currency } from "@/lib/currency"

export function CurrencyToggle({ defaultCurrency = "USD", onChange }: { defaultCurrency?: Currency; onChange: (c: Currency) => void }) {
  const [active, setActive] = useState<Currency>(defaultCurrency)

  function toggle(c: Currency) {
    setActive(c)
    onChange(c)
  }

  return (
    <div className="flex rounded-lg border border-gray-200 dark:border-[#1F1F23] overflow-hidden text-xs font-medium">
      <button
        onClick={() => toggle("USD")}
        className={`px-3 py-1.5 transition-colors ${active === "USD" ? "bg-gray-900 dark:bg-white text-white dark:text-gray-900" : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-[#1F1F23]"}`}
      >USD</button>
      <button
        onClick={() => toggle("KRW")}
        className={`px-3 py-1.5 transition-colors ${active === "KRW" ? "bg-gray-900 dark:bg-white text-white dark:text-gray-900" : "text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-[#1F1F23]"}`}
      >KRW</button>
    </div>
  )
}
