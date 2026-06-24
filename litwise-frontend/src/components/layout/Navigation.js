"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import UserMenu from "../auth/UserMenu";
import {
  BookOpen,
  Upload,
  Search,
  FileText,
  Settings,
  Menu,
  X,
  Library,
  Lightbulb,
  Calendar,
  PenTool,
  ChevronRight,
} from "lucide-react";

const navGroups = [
  {
    label: "Workspace",
    items: [
      { href: "/", label: "Home", icon: BookOpen },
      { href: "/upload", label: "Upload", icon: Upload },
      { href: "/papers", label: "Papers", icon: Library },
    ],
  },
  {
    label: "Tools",
    items: [
      { href: "/literature-review", label: "Literature Review", icon: PenTool },
      { href: "/study-plan", label: "Study Plan", icon: Calendar },
      { href: "/quiz", label: "Quiz", icon: Lightbulb },
      { href: "/research-editor", label: "Editor", icon: FileText },
    ],
  },
  {
    label: "Account",
    items: [
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

// All primary items shown in mobile bottom bar
const mobileTabItems = [
  { href: "/", label: "Home", icon: BookOpen },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/papers", label: "Papers", icon: Library },
  { href: "/literature-review", label: "Review", icon: PenTool },
];

export function Navigation() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const pathname = usePathname();

  const isActive = (href) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  const allItems = navGroups.flatMap((g) => g.items);
  const currentPage = allItems.find((i) => isActive(i.href));

  return (
    <>
      {/* ── Desktop Sidebar ──────────────────────────────────────────── */}
      <nav className="hidden lg:flex fixed left-0 top-0 h-screen w-60 flex-col z-50"
        style={{ background: "linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%)" }}>

        {/* Brand */}
        <Link href="/" className="flex items-center gap-3 px-5 py-5 group">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #6366f1, #06b6d4)" }}>
            <BookOpen className="h-4 w-4 text-white" />
          </div>
          <div>
            <div className="text-white font-bold text-base leading-tight tracking-wide">LitWise</div>
            <div className="text-indigo-300 text-[10px] font-medium tracking-widest uppercase">Research AI</div>
          </div>
        </Link>

        {/* Divider */}
        <div className="mx-5 h-px bg-white/10 mb-2" />

        {/* Nav Groups */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-5">
          {navGroups.map((group) => (
            <div key={group.label}>
              <p className="px-3 mb-1 text-[10px] font-semibold tracking-widest uppercase text-indigo-400">
                {group.label}
              </p>
              <div className="space-y-0.5">
                {group.items.map(({ href, label, icon: Icon }) => {
                  const active = isActive(href);
                  return (
                    <Link key={href} href={href}>
                      <div className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 group relative
                        ${active
                          ? "bg-white/15 text-white"
                          : "text-indigo-200 hover:bg-white/8 hover:text-white"
                        }`}>
                        {active && (
                          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-r-full bg-cyan-400" />
                        )}
                        <Icon className={`h-4 w-4 flex-shrink-0 transition-colors ${active ? "text-cyan-400" : "text-indigo-400 group-hover:text-indigo-200"}`} />
                        <span>{label}</span>
                        {active && <ChevronRight className="ml-auto h-3.5 w-3.5 text-cyan-400 opacity-70" />}
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* User Menu */}
        <div className="p-4 border-t border-white/10">
          <UserMenu />
        </div>
      </nav>

      {/* ── Mobile Top Header ─────────────────────────────────────────── */}
      <header className="lg:hidden fixed top-0 left-0 right-0 h-14 z-50 flex items-center justify-between px-4"
        style={{ background: "linear-gradient(135deg, #0f172a, #1e1b4b)" }}>

        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: "linear-gradient(135deg, #6366f1, #06b6d4)" }}>
            <BookOpen className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="text-white font-bold text-sm tracking-wide">LitWise</span>
        </Link>

        <div className="flex items-center gap-2">
          {/* Current page label */}
          {currentPage && (
            <span className="text-indigo-300 text-xs font-medium px-2 py-1 bg-white/10 rounded-full">
              {currentPage.label}
            </span>
          )}
          <UserMenu />
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/10 text-white transition-colors hover:bg-white/20"
          >
            {isMobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </header>

      {/* ── Mobile Full-Screen Overlay Menu ──────────────────────────── */}
      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 top-14 z-40 overflow-y-auto"
          style={{ background: "linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%)" }}>
          <div className="px-4 pt-5 pb-32 space-y-6">
            {navGroups.map((group) => (
              <div key={group.label}>
                <p className="px-2 mb-2 text-[10px] font-semibold tracking-widest uppercase text-indigo-400">
                  {group.label}
                </p>
                <div className="space-y-1">
                  {group.items.map(({ href, label, icon: Icon }) => {
                    const active = isActive(href);
                    return (
                      <Link key={href} href={href} onClick={() => setIsMobileMenuOpen(false)}>
                        <div className={`flex items-center gap-3.5 px-4 py-3.5 rounded-2xl text-sm font-medium transition-all
                          ${active
                            ? "bg-white/15 text-white"
                            : "text-indigo-200 hover:bg-white/8 hover:text-white"
                          }`}>
                          <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0
                            ${active ? "bg-cyan-500/20" : "bg-white/8"}`}>
                            <Icon className={`h-4 w-4 ${active ? "text-cyan-400" : "text-indigo-400"}`} />
                          </div>
                          <span>{label}</span>
                          {active && <ChevronRight className="ml-auto h-4 w-4 text-cyan-400" />}
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Mobile Bottom Tab Bar ─────────────────────────────────────── */}
      <div className="lg:hidden fixed bottom-0 left-0 right-0 z-50 safe-area-bottom"
        style={{ background: "linear-gradient(180deg, #0f172a, #1e1b4b)", borderTop: "1px solid rgba(255,255,255,0.1)" }}>
        <div className="flex items-center px-2 py-2 gap-1">
          {mobileTabItems.map(({ href, label, icon: Icon }) => {
            const active = isActive(href);
            return (
              <Link key={href} href={href} className="flex-1">
                <div className={`flex flex-col items-center py-1.5 px-1 rounded-xl transition-all
                  ${active ? "bg-white/15" : "hover:bg-white/8"}`}>
                  <Icon className={`h-5 w-5 mb-1 ${active ? "text-cyan-400" : "text-indigo-400"}`} />
                  <span className={`text-[10px] font-medium ${active ? "text-white" : "text-indigo-400"}`}>
                    {label}
                  </span>
                </div>
              </Link>
            );
          })}

          {/* "More" button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="flex-1"
          >
            <div className={`flex flex-col items-center py-1.5 px-1 rounded-xl transition-all
              ${isMobileMenuOpen ? "bg-white/15" : "hover:bg-white/8"}`}>
              <Menu className={`h-5 w-5 mb-1 ${isMobileMenuOpen ? "text-cyan-400" : "text-indigo-400"}`} />
              <span className={`text-[10px] font-medium ${isMobileMenuOpen ? "text-white" : "text-indigo-400"}`}>
                More
              </span>
            </div>
          </button>
        </div>
      </div>
    </>
  );
}
