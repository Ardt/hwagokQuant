"use client";

import { useState, useEffect } from "react";

interface Status {
  trading_enabled: boolean;
  last_signal: { timestamp: string; ticker: string; signal: number } | null;
  last_trade: { timestamp: string; ticker: string; action: string; shares: number; price: number } | null;
  last_snapshot: { timestamp: string; total_value: number } | null;
}

function timeAgo(ts: string): { text: string; stale: boolean } {
  const diff = Date.now() - new Date(ts).getTime();
  const hours = diff / (1000 * 60 * 60);
  if (hours < 1) return { text: `${Math.round(hours * 60)}m ago`, stale: false };
  if (hours < 24) return { text: `${Math.round(hours)}h ago`, stale: false };
  const days = Math.round(hours / 24);
  return { text: `${days}d ago`, stale: days > 1 };
}

export default function StatusPage() {
  const [status, setStatus] = useState<Status | null>(null);

  useEffect(() => {
    fetch("/api/status").then((r) => r.json()).then(setStatus);
    const interval = setInterval(() => {
      fetch("/api/status").then((r) => r.json()).then(setStatus);
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  if (!status) return <div style={{ padding: "2rem" }}>Loading...</div>;

  const signalAge = status.last_signal ? timeAgo(status.last_signal.timestamp) : null;
  const tradeAge = status.last_trade ? timeAgo(status.last_trade.timestamp) : null;
  const snapshotAge = status.last_snapshot ? timeAgo(status.last_snapshot.timestamp) : null;

  return (
    <div>
      <h1>System Status</h1>

      {/* Overall Status */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem", marginBottom: "2rem" }}>
        <StatusCard
          title="Trading"
          value={status.trading_enabled ? "Active" : "Paused"}
          color={status.trading_enabled ? "#4ade80" : "#f87171"}
          icon={status.trading_enabled ? "●" : "⏸"}
        />
        <StatusCard
          title="Last Signal"
          value={signalAge?.text || "Never"}
          color={signalAge?.stale ? "#f87171" : "#4ade80"}
          icon={signalAge?.stale ? "⚠" : "✓"}
        />
        <StatusCard
          title="Last Trade"
          value={tradeAge?.text || "Never"}
          color={tradeAge?.stale ? "#fbbf24" : "#4ade80"}
          icon={tradeAge?.stale ? "⚠" : "✓"}
        />
      </div>

      {/* Details */}
      <section style={{ border: "1px solid #333", borderRadius: "8px", padding: "1.5rem" }}>
        <h2>Latest Activity</h2>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <tbody>
            {status.last_signal && (
              <Row
                label="Last Signal"
                value={`${status.last_signal.ticker} → ${status.last_signal.signal === 1 ? "BUY" : status.last_signal.signal === -1 ? "SELL" : "HOLD"}`}
                time={status.last_signal.timestamp}
              />
            )}
            {status.last_trade && (
              <Row
                label="Last Trade"
                value={`${status.last_trade.action} ${status.last_trade.shares} ${status.last_trade.ticker} @ ${status.last_trade.price.toLocaleString()}`}
                time={status.last_trade.timestamp}
              />
            )}
            {status.last_snapshot && (
              <Row
                label="Portfolio Value"
                value={`${status.last_snapshot.total_value.toLocaleString()}`}
                time={status.last_snapshot.timestamp}
              />
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function StatusCard({ title, value, color, icon }: { title: string; value: string; color: string; icon: string }) {
  return (
    <div style={{ border: "1px solid #333", borderRadius: "8px", padding: "1.5rem", textAlign: "center" }}>
      <div style={{ fontSize: "2rem" }}>{icon}</div>
      <div style={{ color, fontSize: "1.2rem", fontWeight: "bold", margin: "0.5rem 0" }}>{value}</div>
      <div style={{ color: "#888", fontSize: "0.9rem" }}>{title}</div>
    </div>
  );
}

function Row({ label, value, time }: { label: string; value: string; time: string }) {
  return (
    <tr style={{ borderBottom: "1px solid #222" }}>
      <td style={{ padding: "0.75rem", color: "#888" }}>{label}</td>
      <td style={{ padding: "0.75rem" }}>{value}</td>
      <td style={{ padding: "0.75rem", color: "#888", textAlign: "right" }}>{new Date(time).toLocaleString()}</td>
    </tr>
  );
}
