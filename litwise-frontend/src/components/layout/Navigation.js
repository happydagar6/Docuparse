/**
 * Main Navigation Component
 * 
 * Provides app-wide navigation and user interface controls.
 */

"use client";

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  BookOpen, 
  Upload, 
  Search, 
  FileText, 
  Settings,
  Menu,
  X
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/lib/stores';


export function Navigation() {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const pathname = usePathname();
    const { isMobile } = useUIStore();

    const navigationItems = [
    {
      href: '/',
      label: 'Home',
      icon: BookOpen,
      description: 'Dashboard and overview'
    },
    {
      href: '/upload',
      label: 'Upload',
      icon: Upload,
      description: 'Upload new research papers'
    },
    {
      href: '/search',
      label: 'Search',
      icon: Search,
      description: 'Semantic search across papers'
    },
    {
      href: '/papers',
      label: 'Papers',
      icon: FileText,
      description: 'Browse uploaded papers'
    },
  ];

  const isActive = (href) => {
    if(href === '/') {
        return pathname === '/';
    }
    return pathname.startsWith(href);
  };

  return (
    <>
    {/* Desktop Navigation */}
      <nav className="hidden lg:flex fixed left-0 top-0 h-screen w-64 bg-white border-r border-gray-200 flex-col z-50">
        {/* Logo/Brand */}
        <div className="p-6 border-b border-gray-200">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <BookOpen className="h-5 w-5 text-white" />
            </div>
            <span className="text-xl font-bold">Litwise</span>
          </Link>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 py-6">
          <ul className="space-y-2 px-4">
            {navigationItems.map((item) => {
              const IconComponent = item.icon;
              const active = isActive(item.href);
              
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`
                      flex items-center gap-3 px-3 py-2 rounded-lg transition-colors
                      ${active 
                        ? 'bg-primary text-primary-foreground' 
                        : 'text-gray-700 hover:bg-gray-100'
                      }
                    `}
                  >
                    <IconComponent className="h-5 w-5" />
                    <div className="flex-1">
                      <div className="font-medium">{item.label}</div>
                      <div className="text-xs opacity-75">{item.description}</div>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>

        {/* Settings */}
        <div className="p-4 border-t border-gray-200">
          <Button variant="ghost" size="sm" className="w-full justify-start">
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
        </div>
      </nav>

      {/* Mobile Navigation */}
      <div className="lg:hidden">
        {/* Mobile Header */}
        <header className="fixed top-0 left-0 right-0 h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 z-50">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <BookOpen className="h-5 w-5 text-white" />
            </div>
            <span className="text-xl font-bold">Litwise</span>
          </Link>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? (
              <X className="h-6 w-6" />
            ) : (
              <Menu className="h-6 w-6" />
            )}
          </Button>
        </header>

        {/* Mobile Menu Overlay */}
        {isMobileMenuOpen && (
          <div className="fixed inset-0 top-16 bg-white z-40">
            <div className="py-6">
              <ul className="space-y-1 px-4">
                {navigationItems.map((item) => {
                  const IconComponent = item.icon;
                  const active = isActive(item.href);
                  
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        onClick={() => setIsMobileMenuOpen(false)}
                        className={`
                          flex items-center gap-3 px-3 py-3 rounded-lg transition-colors
                          ${active 
                            ? 'bg-primary text-primary-foreground' 
                            : 'text-gray-700 hover:bg-gray-100'
                          }
                        `}
                      >
                        <IconComponent className="h-5 w-5" />
                        <div className="flex-1">
                          <div className="font-medium">{item.label}</div>
                          <div className="text-xs opacity-75">{item.description}</div>
                        </div>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        )}

        {/* Mobile Bottom Navigation */}
        <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50">
          <div className="flex">
            {navigationItems.slice(0, 4).map((item) => {
              const IconComponent = item.icon;
              const active = isActive(item.href);
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`
                    flex-1 flex flex-col items-center py-2 transition-colors
                    ${active ? 'text-primary' : 'text-gray-600'}
                  `}
                >
                  <IconComponent className="h-5 w-5 mb-1" />
                  <span className="text-xs">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}