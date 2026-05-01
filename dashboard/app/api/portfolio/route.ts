import { supabase } from "@/lib/supabase";
import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const id = searchParams.get("id");

  if (id) {
    const { data: portfolio } = await supabase
      .from("portfolios").select("*").eq("id", id).single();
    const { data: holdings } = await supabase
      .from("holdings").select("*").eq("portfolio_id", id);
    const { data: transactions } = await supabase
      .from("transactions").select("*").eq("portfolio_id", id)
      .order("created_at", { ascending: false }).limit(20);
    return NextResponse.json({ portfolio, holdings, transactions });
  }

  const { data } = await supabase.from("portfolios").select("*");
  return NextResponse.json(data);
}
