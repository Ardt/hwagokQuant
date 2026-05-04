import { supabase } from "@/lib/supabase"
import { createSupabaseServer } from "@/lib/supabase-server"
import { WATCHLIST_MAX_PER_MARKET } from "@/lib/constants"
import { NextResponse } from "next/server"

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const portfolioId = searchParams.get("portfolio_id")
  if (!portfolioId) return NextResponse.json({ error: "portfolio_id required" }, { status: 400 })

  const { data } = await supabase
    .from("watchlist")
    .select("*")
    .eq("portfolio_id", portfolioId)

  return NextResponse.json(data || [])
}

function detectMarket(ticker: string): string {
  return /^\d{6}$/.test(ticker) ? "KRX" : "US"
}

export async function POST(req: Request) {
  const serverSupabase = await createSupabaseServer()
  const { data: { user } } = await serverSupabase.auth.getUser()
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

  const { portfolio_id, ticker } = await req.json()
  if (!portfolio_id || !ticker) return NextResponse.json({ error: "Missing fields" }, { status: 400 })

  const upperTicker = ticker.toUpperCase()
  const market = detectMarket(upperTicker)

  // Check per-market limit
  const { data: existing } = await supabase
    .from("watchlist").select("ticker").eq("portfolio_id", portfolio_id)
  const sameMarketCount = (existing || []).filter((w) => detectMarket(w.ticker) === market).length
  if (sameMarketCount >= WATCHLIST_MAX_PER_MARKET) {
    return NextResponse.json({ error: `Watchlist limit is ${WATCHLIST_MAX_PER_MARKET} per market (${market})` }, { status: 400 })
  }

  await supabase.from("watchlist").upsert(
    { portfolio_id, ticker: upperTicker, added_at: new Date().toISOString() },
    { onConflict: "portfolio_id,ticker" }
  )

  return NextResponse.json({ ok: true, ticker: upperTicker })
}

export async function DELETE(req: Request) {
  const serverSupabase = await createSupabaseServer()
  const { data: { user } } = await serverSupabase.auth.getUser()
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

  const { portfolio_id, ticker } = await req.json()
  if (!portfolio_id || !ticker) return NextResponse.json({ error: "Missing fields" }, { status: 400 })

  await supabase.from("watchlist").delete()
    .eq("portfolio_id", portfolio_id)
    .eq("ticker", ticker)

  return NextResponse.json({ ok: true })
}
