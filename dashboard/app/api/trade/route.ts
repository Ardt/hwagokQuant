import { createSupabaseServer } from "@/lib/supabase-server"
import { NextResponse } from "next/server"

export async function POST(req: Request) {
  const supabase = await createSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

  const { portfolio_id, ticker, action, shares, price } = await req.json()

  if (!["BUY", "SELL", "DEPOSIT", "WITHDRAW", "EXCHANGE"].includes(action)) {
    return NextResponse.json({ error: "action must be BUY, SELL, DEPOSIT, WITHDRAW, or EXCHANGE" }, { status: 400 })
  }

  const timestamp = new Date().toISOString()

  // DEPOSIT/WITHDRAW: record as cash transaction
  if (action === "DEPOSIT" || action === "WITHDRAW") {
    const cashCurrency = ticker || "USD"
    const { error } = await supabase.from("transactions").insert({
      portfolio_id, ticker: `CASH_${cashCurrency}`, action, shares: 0, price: Number(price),
      total: Number(price), timestamp, user_id: user.id,
    })
    if (error) return NextResponse.json({ error: error.message }, { status: 400 })
    return NextResponse.json({ ok: true, action, currency: cashCurrency, amount: Number(price) })
  }

  // EXCHANGE: sell one currency, buy another (2 transactions)
  if (action === "EXCHANGE") {
    const fromCur = ticker || "KRW"
    const toCur = fromCur === "USD" ? "KRW" : "USD"
    const exchangeAmount = Number(price)
    const exchangeRate = Number(shares)
    const receivedAmount = fromCur === "KRW" ? exchangeAmount / exchangeRate : exchangeAmount * exchangeRate

    await supabase.from("transactions").insert({
      portfolio_id, ticker: `CASH_${fromCur}`, action: "EXCHANGE", shares: 0,
      price: exchangeAmount, total: exchangeAmount, timestamp, user_id: user.id,
    })
    await supabase.from("transactions").insert({
      portfolio_id, ticker: `CASH_${toCur}`, action: "EXCHANGE", shares: 0,
      price: receivedAmount, total: receivedAmount, timestamp, user_id: user.id,
    })
    return NextResponse.json({ ok: true, action: "EXCHANGE", from: fromCur, to: toCur, amount: exchangeAmount, received: receivedAmount, rate: exchangeRate })
  }

  if (!ticker || !shares || !price) {
    return NextResponse.json({ error: "Missing fields" }, { status: 400 })
  }

  const currency = /^\d{6}$/.test(ticker) ? "KRW" : "USD"
  const total = shares * price

  // Insert transaction
  await supabase.from("transactions").insert({
    portfolio_id, ticker, action, shares, price, total, timestamp, user_id: user.id,
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
        portfolio_id, ticker, shares, avg_cost: price, current_price: price, currency, updated_at: timestamp, user_id: user.id,
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
