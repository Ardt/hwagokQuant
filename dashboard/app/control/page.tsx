"use client";

import { useState, useEffect } from "react";

interface Settings {
  trading_enabled: string;
  signal_threshold: string;
  stop_loss: string;
  take_profit: string;
  max_position_pct: string;
  vix_threshold: string;
}

export default function ControlPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/settings").then((r) => r.json()).then(setSettings);
  }, []);

  async function update(key: string, value: string) {
    setSaving(key);
    await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value }),
    });
    setSettings((s) => (s ? { ...s, [key]: value } : s));
    setSaving(null);
  }

  if (!settings) return <div style={{ padding: "2rem" }}>Loading...</div>;

  const tradingEnabled = settings.trading_enabled === "true";

  return (
    <div>
      <h1>Control Panel</h1>

      {/* Trading Toggle */}
      <section style={{ marginBottom: "2rem", padding: "1.5rem", border: "1px solid #333", borderRadius: "8px" }}>
        <h2>Trading Status</h2>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <button
            onClick={() => update("trading_enabled", tradingEnabled ? "false" : "true")}
            style={{
              padding: "0.75rem 2rem",
              fontSize: "1.1rem",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              background: tradingEnabled ? "#dc2626" : "#16a34a",
              color: "white",
            }}
            disabled={saving === "trading_enabled"}
          >
            {tradingEnabled ? "⏸ Pause Trading" : "▶ Resume Trading"}
          </button>
          <span style={{ color: tradingEnabled ? "#4ade80" : "#f87171", fontSize: "1.1rem" }}>
            {tradingEnabled ? "● Active" : "● Paused"}
          </span>
        </div>
      </section>

      {/* Strategy Parameters */}
      <section style={{ padding: "1.5rem", border: "1px solid #333", borderRadius: "8px" }}>
        <h2>Strategy Parameters</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", maxWidth: "600px" }}>
          <SettingInput
            label="Signal Threshold"
            description="Probability cutoff for BUY signal (0.0 - 1.0)"
            value={settings.signal_threshold}
            onSave={(v) => update("signal_threshold", v)}
            saving={saving === "signal_threshold"}
          />
          <SettingInput
            label="Stop Loss"
            description="Max loss before auto-sell (e.g. -0.05 = -5%)"
            value={settings.stop_loss}
            onSave={(v) => update("stop_loss", v)}
            saving={saving === "stop_loss"}
          />
          <SettingInput
            label="Take Profit"
            description="Target gain to sell (e.g. 0.10 = +10%)"
            value={settings.take_profit}
            onSave={(v) => update("take_profit", v)}
            saving={saving === "take_profit"}
          />
          <SettingInput
            label="Max Position %"
            description="Max portfolio weight per ticker (e.g. 0.25 = 25%)"
            value={settings.max_position_pct}
            onSave={(v) => update("max_position_pct", v)}
            saving={saving === "max_position_pct"}
          />
          <SettingInput
            label="VIX Threshold"
            description="VIX level above which BUY signals are suppressed"
            value={settings.vix_threshold}
            onSave={(v) => update("vix_threshold", v)}
            saving={saving === "vix_threshold"}
          />
        </div>
      </section>
    </div>
  );
}

function SettingInput({ label, description, value, onSave, saving }: {
  label: string; description: string; value: string;
  onSave: (v: string) => void; saving: boolean;
}) {
  const [v, setV] = useState(value);
  const changed = v !== value;

  return (
    <div>
      <label style={{ fontWeight: "bold", display: "block", marginBottom: "0.25rem" }}>{label}</label>
      <p style={{ color: "#888", fontSize: "0.8rem", margin: "0 0 0.5rem" }}>{description}</p>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <input
          type="text"
          value={v}
          onChange={(e) => setV(e.target.value)}
          style={{ padding: "0.4rem", background: "#1a1a1a", border: "1px solid #444", borderRadius: "4px", color: "#ededed", width: "100px" }}
        />
        {changed && (
          <button
            onClick={() => onSave(v)}
            disabled={saving}
            style={{ padding: "0.4rem 0.75rem", background: "#2563eb", color: "white", border: "none", borderRadius: "4px", cursor: "pointer" }}
          >
            {saving ? "..." : "Save"}
          </button>
        )}
      </div>
    </div>
  );
}
