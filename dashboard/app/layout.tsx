import type { Metadata } from "next"
import { SpeedInsights } from "@vercel/speed-insights/next"
import { Analytics } from "@vercel/analytics/next"
import { ThemeProvider } from "@/components/theme-provider"
import Sidebar from "@/components/sidebar"
import TopNav from "@/components/top-nav"
import "./globals.css"

export const metadata: Metadata = {
  title: "Q Dashboard",
  description: "Quant trading system dashboard",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
          <div className="flex h-screen">
            <Sidebar />
            <div className="w-full flex flex-1 flex-col">
              <header className="h-16 border-b border-gray-200 dark:border-[#1F1F23]">
                <TopNav />
              </header>
              <main className="flex-1 overflow-auto p-6 bg-white dark:bg-[#0F0F12]">
                {children}
              </main>
            </div>
          </div>
          <SpeedInsights />
          <Analytics />
        </ThemeProvider>
      </body>
    </html>
  )
}
