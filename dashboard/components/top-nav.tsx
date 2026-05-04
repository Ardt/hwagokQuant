"use client"

import { ThemeToggle } from "./theme-toggle"
import { LogOut } from "lucide-react"
import { createBrowserClient } from "@supabase/ssr"
import { useRouter } from "next/navigation"

export default function TopNav() {
  const router = useRouter()

  async function handleLogout() {
    const supabase = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )
    await supabase.auth.signOut()
    router.push("/login")
  }

  return (
    <nav className="px-4 sm:px-6 flex items-center justify-between bg-white dark:bg-[#0F0F12] border-b border-gray-200 dark:border-[#1F1F23] h-full">
      <div className="text-sm font-medium text-gray-700 dark:text-gray-300 hidden sm:block">
        Quant Trading System
      </div>
      <div className="flex items-center gap-2 ml-auto">
        <ThemeToggle />
        <button
          onClick={handleLogout}
          className="p-2 hover:bg-gray-100 dark:hover:bg-[#1F1F23] rounded-full transition-colors"
          title="Sign out"
        >
          <LogOut className="h-5 w-5 text-gray-600 dark:text-gray-300" />
        </button>
      </div>
    </nav>
  )
}
