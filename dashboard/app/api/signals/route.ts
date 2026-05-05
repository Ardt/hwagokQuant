import { createSupabaseServer } from "@/lib/supabase-server"
import { NextResponse } from "next/server"

export async function GET(req: Request) {
  const supabase = await createSupabaseServer()
  const { searchParams } = new URL(req.url)
  const portfolioId = searchParams.get("portfolio_id")
  const limit = parseInt(searchParams.get("limit") || "50")

  let query = supabase
    .from("signals")
    .select("*")
    .order("timestamp", { ascending: false })
    .limit(limit)

  if (portfolioId) query = query.eq("portfolio_id", portfolioId)

  const { data } = await query
  return NextResponse.json(data)
}
