import { supabase } from "@/lib/supabase";
import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const portfolioId = searchParams.get("portfolio_id");
  const limit = parseInt(searchParams.get("limit") || "50");

  let query = supabase
    .from("signals")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(limit);

  if (portfolioId) query = query.eq("portfolio_id", portfolioId);

  const { data } = await query;
  return NextResponse.json(data);
}
