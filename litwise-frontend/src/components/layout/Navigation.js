/**
 * Enhanced Interactive Navigation Component
 * 
 * Provides app-wide navigation with minimal design patterns,
 * subtle interactions, and modern UI elements.
 */

"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import UserMenu from '../auth/UserMenu';
import { 
  BookOpen, 
  Upload, 
  Search, 
  FileText, 
  Settings,
  Menu,
  X,
  Brain,
  ChevronRight,
  Sparkles,
  Calendar
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/lib/stores';


export function Navigation() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [hoveredItem, setHoveredItem] = useState(null);
  const pathname = usePathname();
  const { isMobile } = useUIStore();

  const navigationItems = [
    {
      href: '/',
      label: 'Home',
      icon: BookOpen,
      description: 'Dashboard and overview',
      color: 'from-blue-500 to-blue-600',
      bgColor: 'bg-blue-50',
      hoverColor: 'hover:bg-blue-100'
    },
    {
      href: '/upload',
      label: 'Upload',
      icon: Upload,
      description: 'Upload new research papers',
      color: 'from-green-500 to-green-600',
      bgColor: 'bg-green-50',
      hoverColor: 'hover:bg-green-100'
    },
    {
      href: '/study-plan',
      label: 'Study Plan',
      icon: Calendar,
      description: 'Generate AI study plans',
      color: 'from-teal-500 to-teal-600',
      bgColor: 'bg-teal-50',
      hoverColor: 'hover:bg-teal-100'
    },
    {
      href: '/search',
      label: 'Search',
      icon: Search,
      description: 'Semantic search across papers',
      color: 'from-purple-500 to-purple-600',
      bgColor: 'bg-purple-50',
      hoverColor: 'hover:bg-purple-100'
    },
    {
      href: '/literature-review',
      label: 'Literature Review',
      icon: Sparkles,
      description: 'Generate literature reviews',
      color: 'from-pink-500 to-pink-600',
      bgColor: 'bg-pink-50',
      hoverColor: 'hover:bg-pink-100'
    },
    {
      href: '/synthesis',
      label: 'History',
      icon: Brain,
      description: 'View saved syntheses',
      color: 'from-indigo-500 to-indigo-600',
      bgColor: 'bg-indigo-50',
      hoverColor: 'hover:bg-indigo-100'
    },
    {
      href: '/papers',
      label: 'Papers',
      icon: FileText,
      description: 'Browse uploaded papers',
      color: 'from-orange-500 to-orange-600',
      bgColor: 'bg-orange-50',
      hoverColor: 'hover:bg-orange-100'
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
      <nav className="hidden lg:flex fixed left-0 top-0 h-screen w-64 bg-white border-r border-gray-200 flex-col z-50 shadow-sm">
        {/* Logo/Brand */}
        <motion.div 
          className="p-6 border-b border-gray-100"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Link href="/" className="flex items-center gap-3 group">
            <motion.div 
              className="w-10 h-10 bg-linear-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg"
              whileHover={{ scale: 1.05, rotate: 5 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <Sparkles className="h-5 w-5 text-white" />
            </motion.div>
            <div>
              <span className="text-xl font-bold bg-linear-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                Litwise
              </span>
              <div className="text-xs text-gray-500">AI Research Assistant</div>
            </div>
          </Link>
        </motion.div>

        {/* User Menu */}
        <div className="flex items-center gap-4">
          {/* ... existing nav items */}
          <UserMenu />
        </div>

        {/* Navigation Items */}
        <div className="flex-1 py-6 px-3">
          <div className="space-y-2">
            {navigationItems.map((item, index) => {
              const IconComponent = item.icon;
              const active = isActive(item.href);
              
              return (
                <motion.div
                  key={item.href}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 + 0.2 }}
                  onMouseEnter={() => setHoveredItem(item.href)}
                  onMouseLeave={() => setHoveredItem(null)}
                >
                  <Link href={item.href}>
                    <motion.div
                      className={`
                        relative flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group cursor-pointer
                        ${active 
                          ? `bg-linear-to-r ${item.color} text-white shadow-lg shadow-blue-200` 
                          : `text-gray-700 ${item.hoverColor} hover:shadow-md hover:scale-[1.02]`
                        }
                      `}
                      whileHover={!active ? { x: 4 } : {}}
                      whileTap={{ scale: 0.98 }}
                    >
                      {/* Active indicator */}
                      {active && (
                        <motion.div
                          className="absolute left-0 top-1/2 w-1 h-8 bg-white rounded-r-full shadow-sm"
                          initial={{ height: 0 }}
                          animate={{ height: 32 }}
                          transition={{ type: "spring", stiffness: 300 }}
                        />
                      )}
                      
                      <motion.div
                        className={`p-2 rounded-lg ${
                          active 
                            ? 'bg-white/20' 
                            : `${item.bgColor} group-hover:scale-110 transition-transform`
                        }`}
                      >
                        <IconComponent className={`h-5 w-5 ${
                          active ? 'text-white' : 'text-gray-600'
                        }`} />
                      </motion.div>
                      
                      <div className="flex-1 min-w-0">
                        <div className={`font-medium ${active ? 'text-white' : 'text-gray-900'}`}>
                          {item.label}
                        </div>
                        <div className={`text-xs mt-0.5 ${
                          active ? 'text-white/80' : 'text-gray-500'
                        }`}>
                          {item.description}
                        </div>
                      </div>

                      {/* Hover arrow */}
                      <AnimatePresence>
                        {hoveredItem === item.href && !active && (
                          <motion.div
                            initial={{ opacity: 0, x: -5 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -5 }}
                            transition={{ duration: 0.2 }}
                          >
                            <ChevronRight className="h-4 w-4 text-gray-400" />
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  </Link>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Settings */}
        <motion.div 
          className="p-4 border-t border-gray-100"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Button 
            variant="ghost" 
            size="sm" 
            className="w-full justify-start hover:bg-gray-100 rounded-xl group"
          >
            <motion.div
              className="p-1.5 bg-gray-100 rounded-lg mr-3 group-hover:bg-gray-200 transition-colors"
              whileHover={{ rotate: 90 }}
              transition={{ duration: 0.3 }}
            >
              <Settings className="h-4 w-4 text-gray-600" />
            </motion.div>
            <span className="text-gray-700">Settings</span>
          </Button>
        </motion.div>
      </nav>

      {/* Mobile Navigation */}
      <div className="lg:hidden">
        {/* Mobile Header */}
        <motion.header 
          className="fixed top-0 left-0 right-0 h-16 bg-white/95 backdrop-blur-sm border-b border-gray-200 flex items-center justify-between px-4 z-50 shadow-sm"
          initial={{ y: -64 }}
          animate={{ y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Link href="/" className="flex items-center gap-3 group">
            <motion.div 
              className="w-8 h-8 bg-linear-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center"
              whileHover={{ scale: 1.1, rotate: 10 }}
              transition={{ type: "spring", stiffness: 400 }}
            >
              <Sparkles className="h-4 w-4 text-white" />
            </motion.div>
            <span className="text-lg font-bold bg-linear-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
              Litwise
            </span>
          </Link>
          
          <motion.div whileTap={{ scale: 0.95 }}>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 hover:bg-gray-100 rounded-xl"
            >
              <motion.div
                animate={{ rotate: isMobileMenuOpen ? 90 : 0 }}
                transition={{ duration: 0.3 }}
              >
                {isMobileMenuOpen ? (
                  <X className="h-6 w-6" />
                ) : (
                  <Menu className="h-6 w-6" />
                )}
              </motion.div>
            </Button>
          </motion.div>
        </motion.header>

        {/* Mobile Menu Overlay */}
        <AnimatePresence>
          {isMobileMenuOpen && (
            <motion.div 
              className="fixed inset-0 top-16 bg-white z-40"
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <div className="py-6 px-4">
                <div className="space-y-2">
                  {navigationItems.map((item, index) => {
                    const IconComponent = item.icon;
                    const active = isActive(item.href);
                    
                    return (
                      <motion.div
                        key={item.href}
                        initial={{ opacity: 0, x: -30 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                      >
                        <Link
                          href={item.href}
                          onClick={() => setIsMobileMenuOpen(false)}
                        >
                          <motion.div
                            className={`
                              flex items-center gap-4 px-4 py-4 rounded-xl transition-all duration-300
                              ${active 
                                ? `bg-linear-to-r ${item.color} text-white shadow-lg` 
                                : `text-gray-700 ${item.hoverColor} hover:shadow-md`
                              }
                            `}
                            whileTap={{ scale: 0.98 }}
                          >
                            <div className={`p-3 rounded-xl ${
                              active 
                                ? 'bg-white/20' 
                                : item.bgColor
                            }`}>
                              <IconComponent className={`h-6 w-6 ${
                                active ? 'text-white' : 'text-gray-600'
                              }`} />
                            </div>
                            <div className="flex-1">
                              <div className={`font-medium text-base ${
                                active ? 'text-white' : 'text-gray-900'
                              }`}>
                                {item.label}
                              </div>
                              <div className={`text-sm ${
                                active ? 'text-white/80' : 'text-gray-500'
                              }`}>
                                {item.description}
                              </div>
                            </div>
                          </motion.div>
                        </Link>
                      </motion.div>
                    );
                  })}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Mobile Bottom Navigation */}
        <motion.div 
          className="lg:hidden fixed bottom-0 left-0 right-0 bg-white/95 backdrop-blur-sm border-t border-gray-200 z-50 shadow-lg"
          initial={{ y: 80 }}
          animate={{ y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <div className="flex px-2 py-2">
            {navigationItems.map((item) => {
              const IconComponent = item.icon;
              const active = isActive(item.href);
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className="flex-1"
                >
                  <motion.div
                    className={`
                      flex flex-col items-center py-2 px-2 rounded-xl transition-all duration-300
                      ${active ? 'text-white' : 'text-gray-600'}
                    `}
                    whileTap={{ scale: 0.95 }}
                  >
                    <motion.div 
                      className={`p-2 rounded-lg mb-1 ${
                        active 
                          ? `bg-linear-to-r ${item.color} shadow-lg` 
                          : 'bg-transparent'
                      }`}
                      whileHover={!active ? { scale: 1.1 } : {}}
                    >
                      <IconComponent className={`h-5 w-5 ${
                        active ? 'text-white' : 'text-gray-600'
                      }`} />
                    </motion.div>
                    <span className={`text-xs font-medium ${
                      active ? 'text-gray-900' : 'text-gray-600'
                    }`}>
                      {item.label}
                    </span>
                  </motion.div>
                </Link>
              );
            })}
          </div>
        </motion.div>
      </div>
    </>
  );
}