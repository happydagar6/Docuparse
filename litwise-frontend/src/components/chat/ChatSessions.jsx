'use client';

import React, { memo } from 'react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { MessageCircle, Trash2, Loader2 } from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';

const ChatSessions = memo(({
  sessions,
  activeSessionId,
  onSessionSelect,
  onSessionDelete,
  isDeleting
}) => {
  if (!sessions.length) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <MessageCircle className="mx-auto h-8 w-8 mb-2 opacity-50" />
        <p className="text-sm">No chat sessions yet</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-[500px]">
      <div className="space-y-1 p-2">
        {sessions.map((session) => (
          <div
            key={session.id}
            className={cn(
              "group flex items-center justify-between p-2 rounded-lg cursor-pointer hover:bg-muted/50 transition-colors",
              activeSessionId === session.id && "bg-muted"
            )}
            onClick={() => onSessionSelect(session.id)}
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {session.title || 'Untitled Chat'}
              </p>
              <p className="text-xs text-muted-foreground">
                {format(new Date(session.updated_at), 'MMM d, h:mm a')}
              </p>
            </div>
            
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="opacity-100 md:opacity-0 group-hover:opacity-100 transition-opacity ml-2 shrink-0"
                  onClick={(e) => e.stopPropagation()}
                  disabled={isDeleting}
                >
                  {isDeleting ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Trash2 className="h-3 w-3" />
                  )}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete Chat Session</AlertDialogTitle>
                  <AlertDialogDescription>
                    Are you sure you want to delete `{session.title}`? This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => onSessionDelete(session.id)}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    Delete
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        ))}
      </div>
    </ScrollArea>
  );
});

ChatSessions.displayName = 'ChatSessions';

export default ChatSessions;