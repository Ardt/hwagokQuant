import { supabase } from "@/lib/supabase";

export default async function SignalsPage() {
  const { data: signals } = await supabase
    .from("signals")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(100);

  return (
    <div>
      <h1>Signals</h1>
      {signals?.length ? (
        <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "0.9rem" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #333" }}>
              <th style={{ textAlign: "left", padding: "0.4rem" }}>Date</th>
              <th style={{ textAlign: "left", padding: "0.4rem" }}>Ticker</th>
              <th style={{ textAlign: "center", padding: "0.4rem" }}>Signal</th>
              <th style={{ textAlign: "right", padding: "0.4rem" }}>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {signals.map((s, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #222" }}>
                <td style={{ padding: "0.4rem" }}>{new Date(s.created_at).toLocaleString()}</td>
                <td style={{ padding: "0.4rem" }}>{s.ticker}</td>
                <td style={{ padding: "0.4rem", textAlign: "center", color: s.signal === 1 ? "#4ade80" : s.signal === -1 ? "#f87171" : "#888" }}>
                  {s.signal === 1 ? "BUY" : s.signal === -1 ? "SELL" : "HOLD"}
                </td>
                <td style={{ padding: "0.4rem", textAlign: "right" }}>{(s.probability * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : <p style={{ color: "#666" }}>No signals yet.</p>}
    </div>
  );
}
