import { supabase } from "@/lib/supabase";

export default async function PortfolioPage() {
  const { data: portfolios } = await supabase.from("portfolios").select("*");

  if (!portfolios?.length) {
    return <div><h1>Portfolio</h1><p style={{ color: "#666" }}>No portfolios.</p></div>;
  }

  // Get holdings for each portfolio
  const details = await Promise.all(
    portfolios.map(async (p) => {
      const { data: holdings } = await supabase
        .from("holdings").select("*").eq("portfolio_id", p.id);
      return { ...p, holdings: holdings || [] };
    })
  );

  return (
    <div>
      <h1>Portfolio</h1>
      {details.map((p) => (
        <section key={p.id} style={{ marginBottom: "2rem", border: "1px solid #222", borderRadius: "8px", padding: "1rem" }}>
          <h2>{p.name}</h2>
          <p style={{ color: "#888" }}>Capital: {p.initial_capital?.toLocaleString()}</p>
          {p.holdings.length ? (
            <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "0.9rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #333" }}>
                  <th style={{ textAlign: "left", padding: "0.4rem" }}>Ticker</th>
                  <th style={{ textAlign: "right", padding: "0.4rem" }}>Shares</th>
                  <th style={{ textAlign: "right", padding: "0.4rem" }}>Avg Cost</th>
                  <th style={{ textAlign: "right", padding: "0.4rem" }}>Current</th>
                </tr>
              </thead>
              <tbody>
                {p.holdings.map((h: any) => (
                  <tr key={h.id} style={{ borderBottom: "1px solid #222" }}>
                    <td style={{ padding: "0.4rem" }}>{h.ticker}</td>
                    <td style={{ padding: "0.4rem", textAlign: "right" }}>{h.shares}</td>
                    <td style={{ padding: "0.4rem", textAlign: "right" }}>{h.avg_cost?.toFixed(2)}</td>
                    <td style={{ padding: "0.4rem", textAlign: "right" }}>{h.current_price?.toFixed(2) || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p style={{ color: "#666" }}>No holdings.</p>}
        </section>
      ))}
    </div>
  );
}
