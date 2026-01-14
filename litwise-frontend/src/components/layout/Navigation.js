/**
 * Navigation Component - Mobile First Design
 *
 * Clean, minimal navigation optimized for mobile and desktop.
 * No animations, focus on usability and clear hierarchy.
 */

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
  Brain,
  PenTool,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUIStore } from "@/lib/stores";

export function Navigation() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const { isMobile } = useUIStore();

  // Primary navigation items - shown in bottom nav on mobile
  const primaryItems = [
    {
      href: "/",
      label: "Home",
      icon: BookOpen,
    },
    {
      href: "/upload",
      label: "Upload",
      icon: Upload,
    },
    {
      href: "/papers",
      label: "Papers",
      icon: Library,
    },
    {
      href: "/search",
      label: "Search",
      icon: Search,
    },
  ];

  // Secondary navigation items - shown in drawer/sidebar
  const secondaryItems = [
    {
      href: "/literature-review",
      label: "Literature Review",
      icon: PenTool,
    },
    {
      href: "/synthesis",
      label: "Synthesis",
      icon: Brain,
    },
    {
      href: "/study-plan",
      label: "Study Plan",
      icon: Calendar,
    },
    {
      href: "/quiz",
      label: "Quiz",
      icon: Lightbulb,
    },
    {
      href: "/research-editor",
      label: "Editor",
      icon: FileText,
    },
    {
      href: "/settings",
      label: "Settings",
      icon: Settings,
    },
  ];

  const isActive = (href) => {
    if (href === "/") {
      return pathname === "/";
    }
    return pathname.startsWith(href);
  };

  // Desktop Navigation
  return (
    <>
      {/* Desktop Sidebar */}
      <nav className="hidden lg:flex fixed left-0 top-0 h-screen w-64 bg-white border-r border-gray-200 flex-col z-50">
        {/* Logo */}
        <div className="p-6 border-b border-gray-200">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <BookOpen className="h-5 w-5 text-white" />
            </div>
            <div>
              <span className="text-lg font-bold text-gray-900">Litwise</span>
              <div className="text-xs text-gray-500">Research</div>
            </div>
          </Link>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 overflow-y-auto py-4 px-3">
          <div className="space-y-1">
            {[...primaryItems, ...secondaryItems].map((item) => {
              const IconComponent = item.icon;
              const active = isActive(item.href);

              return (
                <Link key={item.href} href={item.href}>
                  <div
                    className={`
                      flex items-center gap-3 px-4 py-3 rounded-lg
                      ${
                        active
                          ? "bg-blue-600 text-white"
                          : "text-gray-700 hover:bg-gray-100"
                      }
                    `}
                  >
                    <IconComponent className="h-5 w-5" />
                    <span className="text-sm font-medium">{item.label}</span>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>

        {/* User Menu */}
        <div className="p-4 border-t border-gray-200">
          <UserMenu />
        </div>
      </nav>

      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 z-50">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <BookOpen className="h-4 w-4 text-white" />
          </div>
          <span className="text-base font-bold text-gray-900">Litwise</span>
        </Link>

        <div className="flex items-center gap-3">
          <UserMenu />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="p-2 hover:bg-gray-100"
          >
            {isMobileMenuOpen ? (
              <X className="h-6 w-6" />
            ) : (
              <Menu className="h-6 w-6" />
            )}
          </Button>
        </div>
      </header>

      {/* Mobile Drawer Menu */}
      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 top-16 bg-white z-40 overflow-y-auto">
          <div className="py-4">
            {/* Primary Items */}
            <div className="px-4 pb-4">
              <h3 className="text-xs font-bold text-gray-500 uppercase mb-3">
                Quick Access
              </h3>
              <div className="space-y-1">
                {primaryItems.map((item) => {
                  const IconComponent = item.icon;
                  const active = isActive(item.href);

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      <div
                        className={`
                          flex items-center gap-3 px-4 py-3 rounded-lg
                          ${
                            active
                              ? "bg-blue-600 text-white"
                              : "text-gray-700 hover:bg-gray-100"
                          }
                        `}
                      >
                        <IconComponent className="h-5 w-5" />
                        <span className="text-sm font-medium">{item.label}</span>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>

            {/* Secondary Items */}
            <div className="px-4 border-t border-gray-200 pt-4">
              <h3 className="text-xs font-bold text-gray-500 uppercase mb-3">
                More
              </h3>
              <div className="space-y-1">
                {secondaryItems.map((item) => {
                  const IconComponent = item.icon;
                  const active = isActive(item.href);

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setIsMobileMenuOpen(false)}
                    >
                      <div
                        className={`
                          flex items-center gap-3 px-4 py-3 rounded-lg
                          ${
                            active
                              ? "bg-blue-600 text-white"
                              : "text-gray-700 hover:bg-gray-100"
                          }
                        `}
                      >
                        <IconComponent className="h-5 w-5" />
                        <span className="text-sm font-medium">{item.label}</span>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Mobile Bottom Tab Bar - Only Primary Items */}
      <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50">
        <div className="flex">
          {primaryItems.map((item) => {
            const IconComponent = item.icon;
            const active = isActive(item.href);

            return (
              <Link key={item.href} href={item.href} className="flex-1">
                <div
                  className={`
                    flex flex-col items-center py-3 px-2
                    ${
                      active
                        ? "bg-blue-50 text-blue-600 border-t-2 border-blue-600"
                        : "text-gray-600 border-t-2 border-transparent"
                    }
                  `}
                >
                  <IconComponent className="h-5 w-5 mb-1" />
                  <span className="text-xs font-medium">{item.label}</span>
                </div>
              </Link>
            );
          })}

          {/* Menu button for secondary items */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className={`
              flex flex-col items-center flex-1 py-3 px-2
              ${
                isMobileMenuOpen
                  ? "bg-blue-50 text-blue-600 border-t-2 border-blue-600"
                  : "text-gray-600 border-t-2 border-transparent"
              }
            `}
          >
            <Menu className="h-5 w-5 mb-1" />
            <span className="text-xs font-medium">More</span>
          </button>
        </div>
      </div>
    </>
  );
}
