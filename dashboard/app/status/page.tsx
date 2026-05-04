"use client"

import { useState, useEffect } from "react"
import { Activity, Signal, ArrowRightLeft, Wallet } from "lucide-react"

interface Status {
  trading_enabled: boolean
  last_signal: { timestamp: string; ticker: string; signal: number } | null
  last_trade: { timestamp: string; ticker: string; action: string; shares: number; price: number } | null
  last_snapshot: { timestamp: string; total_value: number } | null
}

function timeAgo(ts: string): { text: string; stale: boolean } {
  const diff = Date.now() - new Date(ts).getTime()
  const hours = diff / (1000 * 60 * 60)
  if (hours < 1) return { text: `${Math.round(hours * 60)}m ago`, stale: false }
  if (hours < 24) return { text: `${Math.round(hours)}h ago`, stale: false }
  return { text: `${Math.round(hours / 24)}d ago`, stale: true }
}

export default function StatusPage() {
  const [status, setStatus] = useState<Status | null>(null)

  useEffect(() => {
    fetch("/api/status").then((r) => r.json()).then(setStatus)
    const interval = setInterval(() => {
      fetch("/api/status").then((r) => r.json()).then(setStatus)
    }, 60000)
    return () => clearInterval(interval)
  }, [])

  if (!status) return <div className="text-gray-500 dark:text-gray-400">Loading...</div>

  const signalAge = status.last_signal ? timeAgo(status.last_signal.timestamp) : null
  const tradeAge = status.last_trade ? timeAgo(status.last_trade.timestamp) : null

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">System Status</h1>

      {/* Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatusCard
          icon={<Activity className="w-5 h-5" />}
          title="Trading"
          value={status.trading_enabled ? "Active" : "Paused"}
          color={status.trading_enabled ? "emerald" : "red"}
        />
        <StatusCard
          icon={<Signal className="w-5 h-5" />}
          title="Last Signal"
          value={signalAge?.text || "Never"}
          color={signalAge?.stale ? "red" : "emerald"}
        />
        <StatusCard
          icon={<ArrowRightLeft className="w-5 h-5" />}
          title="Last Trade"
          value={tradeAge?.text || "Never"}
          color={tradeAge?.stale ? "amber" : "emerald"}
        />
      </div>

      {/* Activity Details */}
      <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-6">
        <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Wallet className="w-4 h-4" />
          Latest Activity
        </h2>
        <div className="space-y-3">
          {status.last_signal && (
            <ActivityRow
              label="Last Signal"
              value={`${status.last_signal.ticker} → ${status.last_signal.signal === 1 ? "BUY" : status.last_signal.signal === -1 ? "SELL" : "HOLD"}`}
              time={status.last_signal.timestamp}
            />
          )}
          {status.last_trade && (
            <ActivityRow
              label="Last Trade"
              value={`${status.last_trade.action} ${status.last_trade.shares} ${status.last_trade.ticker} @ ${status.last_trade.price.toLocaleString()}`}
              time={status.last_trade.timestamp}
            />
          )}
          {status.last_snapshot && (
            <ActivityRow
              label="Portfolio Value"
              value={status.last_snapshot.total_value.toLocaleString()}
              time={status.last_snapshot.timestamp}
            />
          )}
        </div>
      </div>
    </div>
  )
}

function StatusCard({ icon, title, value, color }: { icon: React.ReactNode; title: string; value: string; color: string }) {
  const colorMap: Record<string, string> = {
    emerald: "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20",
    red: "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20",
    amber: "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20",
  }

  return (
    <div className="bg-white dark:bg-[#0F0F12] rounded-xl border border-gray-200 dark:border-[#1F1F23] p-5">
      <div className={`inline-flex p-2 rounded-lg mb-3 ${colorMap[color]}`}>{icon}</div>
      <p className="text-sm text-gray-500 dark:text-gray-400">{title}</p>
      <p className={`text-lg font-semibold mt-1 ${color === "emerald" ? "text-emerald-600 dark:text-emerald-400" : color === "red" ? "text-red-600 dark:text-red-400" : "text-amber-600 dark:text-amber-400"}`}>
        {value}
      </p>
    </div>
  )
}

function ActivityRow({ label, value, time }: { label: string; value: string; time: string }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-[#1F1F23] last:border-0">
      <span className="text-sm text-gray-500 dark:text-gray-400">{label}</span>
      <span className="text-sm font-medium text-gray-900 dark:text-white">{value}</span>
      <span className="text-xs text-gray-400 dark:text-gray-500">{new Date(time).toLocaleString()}</span>
    </div>
  )
}
