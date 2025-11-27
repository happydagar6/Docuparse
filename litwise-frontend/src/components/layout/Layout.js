/**
 * Root Layout Component
 * 
 * Wraps the entire application with providers and layout structure.
 */

'use client';

import { useLayoutEffect, useEffectEvent, startTransition } from 'react';
import { Navigation } from './Navigation';
import { QueryProvider } from '@/lib/react-query';
import { NotificationSystem } from '@/components/ui/notification';
import { useUIStore } from '@/lib/stores';
import InteractiveFooter from './MinimalFooter';

export function RootLayout({ children }) {
  const { setIsMobile } = useUIStore();

  // React 19.2: useEffectEvent for resize handler without dependency issues
  const handleResize = useEffectEvent(() => {
    const isMobile = window.innerWidth < 1024;
    startTransition(() => {
      setIsMobile(isMobile);
    });
  });

  // Detect mobile viewport with useLayoutEffect for synchronous updates
  useLayoutEffect(() => {
    // Initial check
    handleResize();
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []); // 🎉 No dependencies needed!

  return (
    <QueryProvider>
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Navigation />
        
        {/* Main Content Area with sidebar margin */}
        <main className="lg:ml-64 flex-1">
          {children}
        </main>
        
        {/* Footer - positioned after main content, before mobile nav padding */}
        <InteractiveFooter />
        
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
    <div className={`min-h-full ${className}`}>
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
      
      <div className={`${fullWidth ? 'p-6' : 'max-w-7xl mx-auto p-6'} ${!title ? 'pt-16 lg:pt-6' : ''} pb-6`}>
        {children}
      </div>
    </div>
  );
}