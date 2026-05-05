import { createSupabaseServer } from "@/lib/supabase-server"
import { NextResponse } from "next/server"

export async function GET(req: Request) {
  const supabase = await createSupabaseServer()
  const { searchParams } = new URL(req.url)
  const q = searchParams.get("q") || ""
  const limit = parseInt(searchParams.get("limit") || "10")

  if (!q) return NextResponse.json([])

  // Search by ticker or name (case-insensitive)
  const { data } = await supabase
    .from("ticker_names")
    .select("ticker, name")
    .or(`ticker.ilike.%${q}%,name.ilike.%${q}%`)
    .limit(limit)

  return NextResponse.json(data || [])
}
