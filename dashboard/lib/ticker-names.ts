import { supabase } from "./supabase"

/**
 * Lookup names for a list of tickers (batch).
 * Returns a map: { "005930": "삼성전자", "AAPL": "Apple Inc." }
 */
export async function getTickerNames(tickers: string[]): Promise<Record<string, string>> {
  if (!tickers.length) return {}
  const { data } = await supabase
    .from("ticker_names")
    .select("ticker, name")
    .in("ticker", tickers)
  return Object.fromEntries((data || []).map((r) => [r.ticker, r.name]))
}
