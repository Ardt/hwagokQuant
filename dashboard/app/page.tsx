import { supabase } from "@/lib/supabase";

export default async function Home() {
  const { data: portfolios } = await supabase
    .from("portfolios")
    .select("id, name, initial_capital, created_at");

  const { data: recentSignals } = await supabase
    .from("signals")
    .select("ticker, signal, probability, created_at")
    .order("created_at", { ascending: false })
    .limit(10);

  return (
    <div>
      <h1>Overview</h1>
      <section>
        <h2>Portfolios</h2>
        {portfolios?.length ? (
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #333" }}>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>Name</th>
                <th style={{ textAlign: "right", padding: "0.5rem" }}>Capital</th>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>Created</th>
              </tr>
            </thead>
            <tbody>
              {portfolios.map((p) => (
                <tr key={p.id} style={{ borderBottom: "1px solid #222" }}>
                  <td style={{ padding: "0.5rem" }}>{p.name}</td>
                  <td style={{ padding: "0.5rem", textAlign: "right" }}>{p.initial_capital?.toLocaleString()}</td>
                  <td style={{ padding: "0.5rem" }}>{new Date(p.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p style={{ color: "#666" }}>No portfolios yet.</p>}
      </section>

      <section style={{ marginTop: "2rem" }}>
        <h2>Recent Signals</h2>
        {recentSignals?.length ? (
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #333" }}>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>Ticker</th>
                <th style={{ textAlign: "center", padding: "0.5rem" }}>Signal</th>
                <th style={{ textAlign: "right", padding: "0.5rem" }}>Confidence</th>
                <th style={{ textAlign: "left", padding: "0.5rem" }}>Date</th>
              </tr>
            </thead>
            <tbody>
              {recentSignals.map((s, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #222" }}>
                  <td style={{ padding: "0.5rem" }}>{s.ticker}</td>
                  <td style={{ padding: "0.5rem", textAlign: "center", color: s.signal === 1 ? "#4ade80" : s.signal === -1 ? "#f87171" : "#888" }}>
                    {s.signal === 1 ? "BUY" : s.signal === -1 ? "SELL" : "HOLD"}
                  </td>
                  <td style={{ padding: "0.5rem", textAlign: "right" }}>{(s.probability * 100).toFixed(1)}%</td>
                  <td style={{ padding: "0.5rem" }}>{new Date(s.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p style={{ color: "#666" }}>No signals yet.</p>}
      </section>
    </div>
  );
}
