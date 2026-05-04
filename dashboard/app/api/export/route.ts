import { supabase } from "@/lib/supabase"
import { NextResponse } from "next/server"

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const portfolioId = searchParams.get("portfolio_id")
  if (!portfolioId) return NextResponse.json({ error: "portfolio_id required" }, { status: 400 })

  const { data: holdings } = await supabase
    .from("holdings").select("*").eq("portfolio_id", portfolioId)

  if (!holdings?.length) {
    return new NextResponse("No holdings", { status: 404 })
  }

  const headers = ["ticker", "shares", "avg_cost", "current_price", "currency", "market_value", "unrealized_pnl", "pnl_pct"]
  const rows = holdings.map((h) => {
    const price = h.current_price || h.avg_cost
    const marketValue = h.shares * price
    const costBasis = h.shares * h.avg_cost
    const pnl = marketValue - costBasis
    const pnlPct = costBasis ? (pnl / costBasis) : 0
    return [h.ticker, h.shares, h.avg_cost, price, h.currency || "USD", marketValue.toFixed(2), pnl.toFixed(2), (pnlPct * 100).toFixed(2) + "%"].join(",")
  })

  const csv = [headers.join(","), ...rows].join("\n")

  return new NextResponse(csv, {
    headers: {
      "Content-Type": "text/csv",
      "Content-Disposition": `attachment; filename=portfolio_${portfolioId}.csv`,
    },
  })
}
