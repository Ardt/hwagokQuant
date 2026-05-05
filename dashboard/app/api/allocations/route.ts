import { createSupabaseServer } from "@/lib/supabase-server"
import { NextResponse } from "next/server"

export async function GET(req: Request) {
  const supabase = await createSupabaseServer()
  const { searchParams } = new URL(req.url)
  const portfolioId = searchParams.get("portfolio_id")
  if (!portfolioId) return NextResponse.json({ error: "portfolio_id required" }, { status: 400 })

  const { data: allocations } = await supabase
    .from("allocations").select("*").eq("portfolio_id", portfolioId)
  const { data: holdings } = await supabase
    .from("holdings").select("ticker, shares, current_price, avg_cost").eq("portfolio_id", portfolioId)

  const totalValue = (holdings || []).reduce((s: number, h: any) => s + h.shares * (h.current_price || h.avg_cost), 0)
  const currentWeights: Record<string, number> = {}
  for (const h of holdings || []) {
    currentWeights[(h as any).ticker] = totalValue ? (h.shares * (h.current_price || h.avg_cost)) / totalValue : 0
  }

  const suggestions = (allocations || []).map((a: any) => {
    const current = currentWeights[a.ticker] || 0
    const drift = current - a.target_weight
    return { ticker: a.ticker, target: a.target_weight, current, drift }
  })

  return NextResponse.json({ allocations: allocations || [], suggestions })
}

export async function POST(req: Request) {
  const supabase = await createSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

  const { portfolio_id, ticker, target_weight } = await req.json()
  if (!portfolio_id || !ticker || target_weight === undefined) {
    return NextResponse.json({ error: "Missing fields" }, { status: 400 })
  }

  await supabase.from("allocations").upsert(
    { portfolio_id, ticker, target_weight },
    { onConflict: "portfolio_id,ticker" }
  )

  return NextResponse.json({ ok: true })
}

export async function DELETE(req: Request) {
  const supabase = await createSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

  const { portfolio_id, ticker } = await req.json()
  await supabase.from("allocations").delete()
    .eq("portfolio_id", portfolio_id).eq("ticker", ticker)

  return NextResponse.json({ ok: true })
}
