import { createSupabaseServer } from "@/lib/supabase-server"
import { NextResponse } from "next/server"

export async function PUT(req: Request) {
  const supabase = await createSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

  const { portfolio_id, signal_threshold, vix_threshold, max_position_pct, min_cash_pct, allocator_strategy, rotation_metric, rotation_threshold } = await req.json()
  if (!portfolio_id) return NextResponse.json({ error: "portfolio_id required" }, { status: 400 })

  // Validate ranges
  if (signal_threshold < 0.1 || signal_threshold > 0.9) return NextResponse.json({ error: "signal_threshold must be 0.1–0.9" }, { status: 400 })
  if (vix_threshold < 15 || vix_threshold > 50) return NextResponse.json({ error: "vix_threshold must be 15–50" }, { status: 400 })
  if (max_position_pct < 0.05 || max_position_pct > 1.0) return NextResponse.json({ error: "max_position_pct must be 0.05–1.0" }, { status: 400 })
  if (min_cash_pct < 0 || min_cash_pct > 0.9) return NextResponse.json({ error: "min_cash_pct must be 0–0.9" }, { status: 400 })

  const validStrategies = ["equal_weight", "rebalance", "rotation"]
  if (allocator_strategy && !validStrategies.includes(allocator_strategy)) {
    return NextResponse.json({ error: `allocator_strategy must be one of: ${validStrategies.join(", ")}` }, { status: 400 })
  }

  await supabase.from("portfolios").update({
    signal_threshold,
    vix_threshold,
    max_position_pct,
    min_cash_pct,
    ...(allocator_strategy && { allocator_strategy }),
    ...(rotation_metric && { rotation_metric }),
    ...(rotation_threshold != null && { rotation_threshold }),
    updated_at: new Date().toISOString(),
  }).eq("id", portfolio_id)

  return NextResponse.json({ ok: true })
}
