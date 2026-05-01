import { supabase } from "@/lib/supabase";
import { NextResponse } from "next/server";

export async function GET() {
  // Last signal time
  const { data: lastSignal } = await supabase
    .from("signals")
    .select("timestamp, ticker, signal")
    .order("timestamp", { ascending: false })
    .limit(1)
    .single();

  // Last transaction time
  const { data: lastTrade } = await supabase
    .from("transactions")
    .select("timestamp, ticker, action, shares, price")
    .order("timestamp", { ascending: false })
    .limit(1)
    .single();

  // Last snapshot
  const { data: lastSnapshot } = await supabase
    .from("portfolio_snapshots")
    .select("timestamp, total_value")
    .order("timestamp", { ascending: false })
    .limit(1)
    .single();

  // Settings
  const { data: settings } = await supabase.from("settings").select("key, value");
  const settingsMap = Object.fromEntries((settings || []).map((r) => [r.key, r.value]));
  const tradingEnabled = (settingsMap.trading_enabled ?? "true") === "true";

  return NextResponse.json({
    trading_enabled: tradingEnabled,
    last_signal: lastSignal,
    last_trade: lastTrade,
    last_snapshot: lastSnapshot,
  });
}
