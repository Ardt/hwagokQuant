import { supabase } from "@/lib/supabase"
import { Signal, ArrowUpRight, ArrowDownLeft, Minus } from "lucide-react"

export default async function SignalsPage() {
  const { data: signals } = await supabase
    .from("signals")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(100)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Signals</h1>

      <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23]">
        <div className="p-4 border-b border-gray-100 dark:border-[#1F1F23] flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Signal className="w-4 h-4" />
            Recent Signals
            <span className="text-xs font-normal text-gray-500 dark:text-gray-400">({signals?.length || 0})</span>
          </h2>
        </div>

        <div className="p-3 space-y-1">
          {signals?.length ? signals.map((s, i) => (
            <div key={i} className="group flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-[#1F1F23] transition-colors">
              <div className={`p-2 rounded-lg border ${
                s.signal === 1 ? "bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800"
                : s.signal === -1 ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
                : "bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700"
              }`}>
                {s.signal === 1 ? <ArrowUpRight className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  : s.signal === -1 ? <ArrowDownLeft className="w-4 h-4 text-red-600 dark:text-red-400" />
                  : <Minus className="w-4 h-4 text-gray-600 dark:text-gray-400" />}
              </div>

              <div className="flex-1 flex items-center justify-between min-w-0">
                <div>
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white">{s.ticker}</h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400">{new Date(s.created_at).toLocaleString()}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-medium ${
                    s.signal === 1 ? "text-emerald-600 dark:text-emerald-400"
                    : s.signal === -1 ? "text-red-600 dark:text-red-400"
                    : "text-gray-500 dark:text-gray-400"
                  }`}>
                    {s.signal === 1 ? "BUY" : s.signal === -1 ? "SELL" : "HOLD"}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {(s.probability * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          )) : (
            <p className="text-sm text-gray-500 dark:text-gray-400 p-3">No signals yet.</p>
          )}
        </div>
      </div>
    </div>
  )
}
