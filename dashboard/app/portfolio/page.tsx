import { createSupabaseServer } from "@/lib/supabase-server"
import { getTickerNames } from "@/lib/ticker-names"
import { getLatestRate } from "@/lib/currency"
import { computeSharpe, computeMaxDrawdown, computeRealizedPnl, computeInformationRatio } from "@/lib/analytics"
import { TradeForm } from "@/components/trade-form"
import { CreatePortfolio } from "@/components/portfolio-manage"
import { PortfolioContent } from "@/components/portfolio-content"

export default async function PortfolioPage() {
  const supabase = await createSupabaseServer()
  const { data: portfolios } = await supabase.from("portfolios").select("*")

  if (!portfolios?.length) {
    return (
      <div>
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Portfolio</h1>
          <CreatePortfolio />
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">No portfolios yet. Create one to get started.</p>
      </div>
    )
  }

  const details = await Promise.all(
    portfolios.map(async (p) => {
      const { data: holdings } = await supabase.from("holdings").select("*").eq("portfolio_id", p.id)
      const { data: snapshots } = await supabase
        .from("portfolio_snapshots").select("timestamp, total_value")
        .eq("portfolio_id", p.id).order("timestamp", { ascending: true })
      const { data: transactions } = await supabase
        .from("transactions").select("*")
        .eq("portfolio_id", p.id).order("timestamp", { ascending: true })
      const { data: watchlist } = await supabase
        .from("watchlist").select("ticker")
        .eq("portfolio_id", p.id)

      const sharpe = computeSharpe(snapshots || [])
      const maxDrawdown = computeMaxDrawdown(snapshots || [])
      const realizedPnl = computeRealizedPnl(transactions || [])
      const recentTxns = [...(transactions || [])].reverse().slice(0, 20)

      // Compute information ratio vs benchmark
      let infoRatio = 0
      if (snapshots && snapshots.length > 2) {
        const snapshotDates = snapshots.map((s: any) => s.timestamp?.slice(0, 10))
        const { data: benchData } = await supabase
          .from("benchmarks")
          .select("date, close")
          .in("date", snapshotDates)
          .eq("ticker", holdings?.some((h: any) => /^\d{6}$/.test(h.ticker)) ? "KOSPI" : "NASDAQ100")
          .order("date", { ascending: true })
        if (benchData && benchData.length > 2) {
          infoRatio = computeInformationRatio(snapshots, benchData.map((b: any) => b.close))
        }
      }

      return { ...p, holdings: holdings || [], snapshots: snapshots || [], transactions: recentTxns, allTransactions: transactions || [], watchlist: watchlist || [], sharpe, maxDrawdown, realizedPnl, infoRatio }
    })
  )

  const allTickers = details.flatMap((p) => [
    ...p.holdings.map((h: any) => h.ticker),
    ...p.transactions.map((t: any) => t.ticker),
    ...p.watchlist.map((w: any) => w.ticker),
  ])
  const names = await getTickerNames(Array.from(new Set(allTickers)))
  const rate = await getLatestRate()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Portfolio</h1>
        <div className="flex items-center gap-2">
          <CreatePortfolio />
          <TradeForm portfolios={portfolios.map((p) => ({ id: p.id, name: p.name }))} />
        </div>
      </div>

      <PortfolioContent portfolios={details} names={names} rate={rate} />
    </div>
  )
}
