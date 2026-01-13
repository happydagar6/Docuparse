'use client';

import React, { memo } from 'react';
import { Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * ReasoningIndicator Component
 * 
 * Clean, interactive indicator showing AI reasoning in progress.
 * Features smooth animations and modern color scheme.
 */
const ReasoningIndicator = memo(function ReasoningIndicator({ className = '' }) {
  return (
    <div className={cn(
      'mb-3 md:mb-4',
      'animate-in fade-in duration-300',
      className
    )}>
      {/* Main Container - Clean and Minimal */}
      <div className="relative overflow-hidden rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/50 px-3 md:px-4 py-2.5 md:py-3">
        
        {/* Subtle animated background */}
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-blue-100/30 to-transparent opacity-0 animate-pulse" style={{ animation: 'pulse 3s ease-in-out infinite' }} />
        
        {/* Content */}
        <div className="relative flex items-center gap-2.5 md:gap-3">
          
          {/* Animated Zap Icon */}
          <div className="flex items-center justify-center shrink-0">
            <div className="relative w-5 h-5 md:w-6 md:h-6">
              <Zap className="h-full w-full text-indigo-600 animate-pulse" style={{ animation: 'pulse 2s ease-in-out infinite' }} />
              
              {/* Subtle animation glow */}
              <div className="absolute inset-0 rounded-full opacity-0" style={{ 
                animation: 'scale-glow 2s ease-in-out infinite',
                boxShadow: '0 0 12px rgba(79, 70, 229, 0.3)'
              }} />
            </div>
          </div>
          
          {/* Text Content */}
          <div className="flex-1">
            <p className="text-xs md:text-sm font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-blue-600 to-indigo-600 leading-tight" style={{ animation: 'text-shimmer 2s ease-in-out infinite' }}>
              Reasoning: Processing your query
            </p>
          </div>
          
          {/* Interactive Animated Dots */}
          <div className="flex items-center gap-1 shrink-0">
            <div 
              className="w-1.5 h-1.5 rounded-full bg-indigo-600"
              style={{ animation: 'dot-pulse 1.4s ease-in-out infinite 0s' }}
            />
            <div 
              className="w-1.5 h-1.5 rounded-full bg-indigo-500"
              style={{ animation: 'dot-pulse 1.4s ease-in-out infinite 0.2s' }}
            />
            <div 
              className="w-1.5 h-1.5 rounded-full bg-indigo-400"
              style={{ animation: 'dot-pulse 1.4s ease-in-out infinite 0.4s' }}
            />
          </div>
        </div>

        {/* Inline Styles for Custom Animations */}
        <style>{`
          @keyframes text-shimmer {
            0% {
              background-position: -200% 0;
              opacity: 0.8;
            }
            50% {
              opacity: 1;
            }
            100% {
              background-position: 200% 0;
              opacity: 0.8;
            }
          }
          
          @keyframes dot-pulse {
            0%, 100% {
              opacity: 0.4;
              transform: translateY(0) scale(1);
            }
            50% {
              opacity: 1;
              transform: translateY(-5px) scale(1.1);
            }
          }
          
          @keyframes scale-glow {
            0%, 100% {
              opacity: 0;
              transform: scale(1);
            }
            50% {
              opacity: 0.6;
              transform: scale(1.4);
            }
          }
        `}</style>
      </div>
    </div>
  );
});

ReasoningIndicator.displayName = 'ReasoningIndicator';

export default ReasoningIndicator;
