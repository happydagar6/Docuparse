/**
 * Progress Component
 * 
 * Progress bar for upload and loading states
 */

import { cn } from '@/lib/utils';

export function Progress({ className, value, ...props }) {
  return (
    <div
      className={cn(
        "relative h-4 w-full overflow-hidden rounded-full bg-secondary",
        className
      )}
      {...props}
    >
      <div
        className="h-full w-full flex-1 bg-primary transition-all duration-300 ease-in-out"
        style={{
          transform: `translateX(-${100 - (value || 0)}%)`,
        }}
      />
    </div>
  );
}