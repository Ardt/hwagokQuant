import { createSupabaseServer } from "@/lib/supabase-server"
import { NextResponse } from "next/server"

export async function GET(req: Request) {
  const supabase = await createSupabaseServer()
  const { searchParams } = new URL(req.url)
  const id = searchParams.get("id")

  if (id) {
    const { data: portfolio } = await supabase
      .from("portfolios").select("*").eq("id", id).single()
    const { data: holdings } = await supabase
      .from("holdings").select("*").eq("portfolio_id", id)
    const { data: transactions } = await supabase
      .from("transactions").select("*").eq("portfolio_id", id)
      .order("created_at", { ascending: false }).limit(20)
    return NextResponse.json({ portfolio, holdings, transactions })
  }

  const { data } = await supabase.from("portfolios").select("*")
  return NextResponse.json(data)
}

export async function POST(req: Request) {
  const supabase = await createSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

  const { name } = await req.json()
  if (!name) return NextResponse.json({ error: "name required" }, { status: 400 })

  const now = new Date().toISOString()
  const { data, error } = await supabase.from("portfolios").insert({
    name,
    user_id: user.id,
    created_at: now,
    updated_at: now,
  }).select().single()

  if (error) return NextResponse.json({ error: error.message }, { status: 400 })
  return NextResponse.json(data)
}

export async function DELETE(req: Request) {
  const supabase = await createSupabaseServer()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 })

  const { id } = await req.json()
  if (!id) return NextResponse.json({ error: "id required" }, { status: 400 })

  await supabase.from("watchlist").delete().eq("portfolio_id", id)
  await supabase.from("signals").delete().eq("portfolio_id", id)
  await supabase.from("transactions").delete().eq("portfolio_id", id)
  await supabase.from("holdings").delete().eq("portfolio_id", id)
  await supabase.from("portfolio_snapshots").delete().eq("portfolio_id", id)
  await supabase.from("portfolios").delete().eq("id", id)

  return NextResponse.json({ ok: true })
}
