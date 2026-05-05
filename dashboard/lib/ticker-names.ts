import { supabase } from "./supabase"

/**
 * Lookup names for a list of tickers (batch).
 * Returns a map: { "005930": "삼성전자", "AAPL": "Apple Inc." }
 */
export async function getTickerNames(tickers: string[]): Promise<Record<string, string>> {
  if (!tickers.length) return {}
  const unique = Array.from(new Set(tickers))
  const results: Record<string, string> = {}

  // Chunk into batches of 50 to avoid Supabase .in() limits
  for (let i = 0; i < unique.length; i += 50) {
    const chunk = unique.slice(i, i + 50)
    const { data } = await supabase
      .from("ticker_names")
      .select("ticker, name")
      .in("ticker", chunk)
    if (data) {
      for (const r of data) results[r.ticker] = r.name
    }
  }
  return results
}
