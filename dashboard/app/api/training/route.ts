import { fetchResults } from "@/lib/storage";
import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const market = searchParams.get("market") || "us";

  const filename = market === "us" ? "training_results.csv" : `training_results_${market}.csv`;
  const csv = await fetchResults(filename);

  if (!csv) return NextResponse.json({ error: "No results available" }, { status: 404 });

  // Parse CSV to JSON
  const lines = csv.trim().split("\n");
  const headers = lines[0].split(",");
  const rows = lines.slice(1).map((line) => {
    const values = line.split(",");
    const row: Record<string, string | number> = {};
    headers.forEach((h, i) => {
      const v = values[i];
      row[h] = isNaN(Number(v)) ? v : Number(v);
    });
    return row;
  });

  return NextResponse.json(rows);
}
