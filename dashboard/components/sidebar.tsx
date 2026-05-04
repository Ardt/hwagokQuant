"use client"

import { Home, BarChart2, Briefcase, Signal, Settings, Activity, Menu } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useState } from "react"
import { cn } from "@/lib/utils"

const navItems = [
  { href: "/", icon: Home, label: "Dashboard" },
  { href: "/training", icon: BarChart2, label: "Training" },
  { href: "/portfolio", icon: Briefcase, label: "Portfolio" },
  { href: "/signals", icon: Signal, label: "Signals" },
  { href: "/control", icon: Settings, label: "Control" },
  { href: "/status", icon: Activity, label: "Status" },
]

export default function Sidebar() {
  const [open, setOpen] = useState(false)
  const pathname = usePathname()

  return (
    <>
      <button
        type="button"
        className="lg:hidden fixed top-4 left-4 z-[70] p-2 rounded-lg bg-white dark:bg-[#0F0F12] shadow-md"
        onClick={() => setOpen(!open)}
      >
        <Menu className="h-5 w-5 text-gray-600 dark:text-gray-300" />
      </button>

      <nav className={cn(
        "fixed inset-y-0 left-0 z-[70] w-64 bg-white dark:bg-[#0F0F12] transform transition-transform duration-200 ease-in-out",
        "lg:translate-x-0 lg:static lg:w-64 border-r border-gray-200 dark:border-[#1F1F23]",
        open ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="h-full flex flex-col">
          <div className="h-16 px-6 flex items-center border-b border-gray-200 dark:border-[#1F1F23]">
            <span className="text-lg font-semibold text-gray-900 dark:text-white">Q Dashboard</span>
          </div>

          <div className="flex-1 overflow-y-auto py-4 px-4">
            <div className="px-3 mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
              Navigation
            </div>
            <div className="space-y-1">
              {navItems.map(({ href, icon: Icon, label }) => (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setOpen(false)}
                  className={cn(
                    "flex items-center px-3 py-2 text-sm rounded-md transition-colors",
                    pathname === href
                      ? "bg-gray-100 dark:bg-[#1F1F23] text-gray-900 dark:text-white font-medium"
                      : "text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-[#1F1F23]"
                  )}
                >
                  <Icon className="h-4 w-4 mr-3 flex-shrink-0" />
                  {label}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </nav>

      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-[65] lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}
    </>
  )
}
