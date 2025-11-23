/**
 * Root Layout Component
 * 
 * Wraps the entire application with providers and layout structure.
 */

'use client';

import { useEffect } from 'react';
import { Navigation } from './Navigation';
import { QueryProvider } from '@/lib/react-query';
import { NotificationSystem } from '@/components/ui/notification';
import { useUIStore } from '@/lib/stores';

export function RootLayout({ children }) {
  const { setIsMobile } = useUIStore();

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [setIsMobile]);

  return (
    <QueryProvider>
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        
        {/* Main Content Area */}
        <main className="lg:ml-64 min-h-screen">
          {children}
        </main>
        
        {/* Mobile padding for bottom navigation */}
        <div className="lg:hidden h-16" />
        
        {/* Notification System */}
        <NotificationSystem />
      </div>
    </QueryProvider>
  );
}

/**
 * Page Layout Component
 * 
 * Standard page wrapper with consistent padding and structure.
 */
export function PageLayout({ 
  title, 
  description, 
  children,
  className = '',
  fullWidth = false 
}) {
  return (
    <div className={`min-h-screen ${className}`}>
      {title && (
        <div className="bg-white border-b border-gray-200 py-8">
          <div className={`${fullWidth ? 'px-6' : 'max-w-7xl mx-auto px-6'}`}>
            <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
            {description && (
              <p className="mt-2 text-gray-600">{description}</p>
            )}
          </div>
        </div>
      )}
      
      <div className={`${fullWidth ? 'p-6' : 'max-w-7xl mx-auto p-6'} ${!title ? 'pt-16 lg:pt-6' : ''}`}>
        {children}
      </div>
    </div>
  );
}