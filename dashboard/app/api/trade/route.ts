import { createSupabaseServer } from "@/lib/supabase-server"
import { NextResponse } from "next/server"

export async function POST(req: Request) {
  const supabase = await createSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

  const { portfolio_id, ticker, action, shares, price } = await req.json()

  if (!portfolio_id || !ticker || !action || !shares || !price) {
    return NextResponse.json({ error: "Missing fields" }, { status: 400 })
  }
  if (!["BUY", "SELL"].includes(action)) {
    return NextResponse.json({ error: "action must be BUY or SELL" }, { status: 400 })
  }

  const total = shares * price
  const timestamp = new Date().toISOString()

  // Insert transaction
  await supabase.from("transactions").insert({
    portfolio_id, ticker, action, shares, price, total, timestamp, source: "manual", user_id: user.id,
  })

  // Update holdings
  const { data: existing } = await supabase
    .from("holdings").select("*").eq("portfolio_id", portfolio_id).eq("ticker", ticker).single()

  if (action === "BUY") {
    if (existing) {
      const newShares = existing.shares + shares
      const avgCost = (existing.shares * existing.avg_cost + shares * price) / newShares
      await supabase.from("holdings")
        .update({ shares: newShares, avg_cost: avgCost, current_price: price, updated_at: timestamp })
        .eq("id", existing.id)
    } else {
      await supabase.from("holdings").insert({
        portfolio_id, ticker, shares, avg_cost: price, current_price: price, updated_at: timestamp, user_id: user.id,
      })
    }
  } else {
    if (!existing) return NextResponse.json({ error: "No holding to sell" }, { status: 400 })
    const remaining = existing.shares - shares
    if (remaining <= 0) {
      await supabase.from("holdings").delete().eq("id", existing.id)
    } else {
      await supabase.from("holdings")
        .update({ shares: remaining, current_price: price, updated_at: timestamp })
        .eq("id", existing.id)
    }
  }

  return NextResponse.json({ ok: true, action, ticker, shares, price, total })
}
