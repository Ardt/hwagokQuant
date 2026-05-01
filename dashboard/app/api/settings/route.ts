import { supabase } from "@/lib/supabase";
import { NextResponse } from "next/server";

export async function GET() {
  const { data } = await supabase.from("settings").select("key, value, updated_at");

  const defaults: Record<string, string> = {
    trading_enabled: "true",
    signal_threshold: "0.5",
    stop_loss: "-0.05",
    take_profit: "0.10",
    max_position_pct: "0.25",
    vix_threshold: "30",
  };

  const stored = Object.fromEntries((data || []).map((r) => [r.key, r.value]));
  return NextResponse.json({ ...defaults, ...stored });
}

export async function PUT(req: Request) {
  const body = await req.json();
  const { key, value } = body;

  if (!key || value === undefined) {
    return NextResponse.json({ error: "key and value required" }, { status: 400 });
  }

  const { data: existing } = await supabase
    .from("settings").select("id").eq("key", key).single();

  if (existing) {
    await supabase.from("settings")
      .update({ value: String(value), updated_at: new Date().toISOString() })
      .eq("key", key);
  } else {
    await supabase.from("settings")
      .insert({ key, value: String(value), updated_at: new Date().toISOString() });
  }

  return NextResponse.json({ key, value: String(value) });
}
