import { fetchResults } from "@/lib/storage";

async function getResults(market: string) {
  const filename = market === "us" ? "training_results.csv" : `training_results_${market}.csv`;
  const csv = await fetchResults(filename);
  if (!csv) return [];
  const lines = csv.trim().split("\n");
  const headers = lines[0].split(",");
  return lines.slice(1).map((line) => {
    const values = line.split(",");
    const row: Record<string, any> = {};
    headers.forEach((h, i) => { row[h] = isNaN(Number(values[i])) ? values[i] : Number(values[i]); });
    return row;
  });
}

export default async function TrainingPage() {
  const usResults = await getResults("us");
  const krxResults = await getResults("krx");

  const renderTable = (results: any[], title: string) => (
    <section style={{ marginBottom: "2rem" }}>
      <h2>{title} ({results.length} tickers)</h2>
      {results.length ? (
        <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "0.9rem" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #333" }}>
              <th style={{ textAlign: "left", padding: "0.4rem" }}>Ticker</th>
              <th style={{ textAlign: "right", padding: "0.4rem" }}>Return</th>
              <th style={{ textAlign: "right", padding: "0.4rem" }}>Sharpe</th>
              <th style={{ textAlign: "right", padding: "0.4rem" }}>Win Rate</th>
              <th style={{ textAlign: "right", padding: "0.4rem" }}>Max DD</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #222" }}>
                <td style={{ padding: "0.4rem" }}>{r.ticker}</td>
                <td style={{ padding: "0.4rem", textAlign: "right", color: r.total_return > 0 ? "#4ade80" : "#f87171" }}>
                  {(r.total_return * 100).toFixed(1)}%
                </td>
                <td style={{ padding: "0.4rem", textAlign: "right" }}>{r.sharpe_ratio?.toFixed(2)}</td>
                <td style={{ padding: "0.4rem", textAlign: "right" }}>{(r.win_rate * 100).toFixed(0)}%</td>
                <td style={{ padding: "0.4rem", textAlign: "right", color: "#f87171" }}>
                  {(r.max_drawdown * 100).toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : <p style={{ color: "#666" }}>No results available. Configure OCI_RESULTS_URL.</p>}
    </section>
  );

  return (
    <div>
      <h1>Training Results</h1>
      {renderTable(usResults, "US Market")}
      {renderTable(krxResults, "KRX Market")}
    </div>
  );
}
