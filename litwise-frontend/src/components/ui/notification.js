/**
 * Notification System Component
 * 
 * Displays toast notifications for user feedback across the app.
 */

'use client';

import { useLayoutEffect, useCallback, useEffectEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircle, 
  AlertCircle, 
  XCircle, 
  Info, 
  X 
} from 'lucide-react';
import { useUIStore } from '@/lib/stores';

export function NotificationSystem() {
  const { notifications, removeNotification } = useUIStore();

  // React 19.2: useEffectEvent to access latest removeNotification without effect re-runs
  const setupAutoRemoval = useEffectEvent((notification) => {
    if (notification.autoRemove !== false) {
      const timeoutId = setTimeout(() => {
        removeNotification(notification.id);
      }, 5000);
      return timeoutId;
    }
    return null;
  });

  useLayoutEffect(() => {
    const timeouts = [];
    
    notifications.forEach((notification) => {
      const timeoutId = setupAutoRemoval(notification);
      if (timeoutId) {
        timeouts.push(timeoutId);
      }
    });

    return () => {
      timeouts.forEach(clearTimeout);
    };
  }, [notifications]); // ✅ Only notifications - setupAutoRemoval doesn't trigger re-runs

  const getIcon = (type) => {
    switch (type) {
      case 'success':
        return CheckCircle;
      case 'error':
        return XCircle;
      case 'warning':
        return AlertCircle;
      default:
        return Info;
    }
  };

  const getStyles = (type) => {
    switch (type) {
      case 'success':
        return 'bg-green-50 border-green-200 text-green-800';
      case 'error':
        return 'bg-red-50 border-red-200 text-red-800';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800';
      default:
        return 'bg-blue-50 border-blue-200 text-blue-800';
    }
  };

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
      <AnimatePresence>
        {notifications.map((notification) => {
          const IconComponent = getIcon(notification.type);
          
          return (
            <motion.div
              key={notification.id}
              initial={{ opacity: 0, x: 300, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 300, scale: 0.9 }}
              className={`
                border rounded-lg p-4 shadow-lg backdrop-blur-sm
                ${getStyles(notification.type)}
              `}
            >
              <div className="flex items-start gap-3">
                <IconComponent className="h-5 w-5 mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  {notification.title && (
                    <h4 className="font-medium mb-1">
                      {notification.title}
                    </h4>
                  )}
                  <p className="text-sm">
                    {notification.message}
                  </p>
                </div>
                <button
                  onClick={() => removeNotification(notification.id)}
                  className="text-current opacity-60 hover:opacity-100 transition-opacity"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}