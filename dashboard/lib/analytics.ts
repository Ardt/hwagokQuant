/** Compute portfolio risk metrics from snapshots. */

export function computeSharpe(snapshots: { total_value: number }[], riskFree = 0.02): number {
  if (snapshots.length < 3) return 0
  const values = snapshots.map((s) => s.total_value)
  const returns: number[] = []
  for (let i = 1; i < values.length; i++) {
    returns.push((values[i] - values[i - 1]) / values[i - 1])
  }
  const mean = returns.reduce((a, b) => a + b, 0) / returns.length
  const std = Math.sqrt(returns.reduce((a, b) => a + (b - mean) ** 2, 0) / returns.length)
  if (std === 0) return 0
  const dailyRf = riskFree / 252
  return ((mean - dailyRf) / std) * Math.sqrt(252)
}

export function computeMaxDrawdown(snapshots: { total_value: number }[]): number {
  if (snapshots.length < 2) return 0
  const values = snapshots.map((s) => s.total_value)
  let peak = values[0]
  let maxDd = 0
  for (const v of values) {
    if (v > peak) peak = v
    const dd = (v - peak) / peak
    if (dd < maxDd) maxDd = dd
  }
  return maxDd
}

export function computeRealizedPnl(transactions: { ticker: string; action: string; shares: number; price: number; timestamp: string }[]) {
  const buys: Record<string, { shares: number; price: number }[]> = {}
  const realized: { ticker: string; shares: number; sell_price: number; cost_basis: number; pnl: number; timestamp: string }[] = []

  for (const t of transactions) {
    if (t.action === "BUY") {
      if (!buys[t.ticker]) buys[t.ticker] = []
      buys[t.ticker].push({ shares: t.shares, price: t.price })
    } else {
      let remaining = t.shares
      let cost = 0
      while (remaining > 0 && buys[t.ticker]?.length) {
        const lot = buys[t.ticker][0]
        const used = Math.min(remaining, lot.shares)
        cost += used * lot.price
        lot.shares -= used
        remaining -= used
        if (lot.shares <= 0) buys[t.ticker].shift()
      }
      realized.push({
        ticker: t.ticker,
        shares: t.shares,
        sell_price: t.price,
        cost_basis: cost,
        pnl: t.shares * t.price - cost,
        timestamp: t.timestamp,
      })
    }
  }
  return realized
}
