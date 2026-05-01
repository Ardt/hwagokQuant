import type { Metadata } from "next";
import { SpeedInsights } from "@vercel/speed-insights/next";

export const metadata: Metadata = {
  title: "Q Dashboard",
  description: "Quant trading system dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, sans-serif", background: "#0a0a0a", color: "#ededed" }}>
        <nav style={{ padding: "1rem 2rem", borderBottom: "1px solid #222", display: "flex", gap: "2rem" }}>
          <a href="/" style={{ color: "#ededed", textDecoration: "none", fontWeight: "bold" }}>Q Dashboard</a>
          <a href="/training" style={{ color: "#888", textDecoration: "none" }}>Training</a>
          <a href="/portfolio" style={{ color: "#888", textDecoration: "none" }}>Portfolio</a>
          <a href="/signals" style={{ color: "#888", textDecoration: "none" }}>Signals</a>
          <a href="/control" style={{ color: "#888", textDecoration: "none" }}>Control</a>
          <a href="/status" style={{ color: "#888", textDecoration: "none" }}>Status</a>
        </nav>
        <main style={{ padding: "2rem" }}>{children}</main>
        <SpeedInsights />
        <Analytics />
      </body>
    </html>
  );
}
   </body>
    </html>
  );
}
