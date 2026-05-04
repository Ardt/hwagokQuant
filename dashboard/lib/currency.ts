import { supabase } from "./supabase"

export type Currency = "USD" | "KRW"

export const CURRENCY_SYMBOLS: Record<Currency, string> = {
  USD: "$",
  KRW: "₩",
}

/** Get latest exchange rate for USD/KRW */
export async function getLatestRate(): Promise<number> {
  const { data } = await supabase
    .from("exchange_rates")
    .select("rate")
    .eq("pair", "USD/KRW")
    .order("date", { ascending: false })
    .limit(1)
    .single()
  return data?.rate || 1370 // fallback
}

/** Convert value from one currency to another */
export function convert(value: number, from: Currency, to: Currency, rate: number): number {
  if (from === to) return value
  if (from === "USD" && to === "KRW") return value * rate
  if (from === "KRW" && to === "USD") return value / rate
  return value
}

/** Format value with currency symbol */
export function formatCurrency(value: number, currency: Currency): string {
  if (currency === "KRW") return `₩${Math.round(value).toLocaleString()}`
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
