'use client';

import { useEffect, useCallback, useMemo, memo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMultiModalContent } from '@/lib/multimodal-api';
import { useMultiModalStore } from '@/lib/stores';
import { ImageContent } from './ImageContent';
import { TableContent } from './TableContent';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Loader2, 
  AlertCircle, 
  ImageIcon, 
  TableIcon, 
  RefreshCcw,
  FileSearch 
} from 'lucide-react';

/**
 * Empty State Component - Memoized
 */
const EmptyState = memo(function EmptyState({ type }) {
  const config = {
    empty: {
      icon: FileSearch,
      title: 'No Multi-Modal Content',
      description: 'This paper doesn\'t contain any images or tables.',
    },
    error: {
      icon: AlertCircle,
      title: 'Failed to Load Content',
      description: 'There was an error loading images and tables.',
    },
  };

  const { icon: Icon, title, description } = config[type] || config.empty;

  return (
    <Card className="p-8">
      <div className="flex flex-col items-center justify-center text-center space-y-3">
        <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center">
          <Icon className="h-8 w-8 text-muted-foreground" />
        </div>
        <div className="space-y-1">
          <h3 className="font-medium">{title}</h3>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
    </Card>
  );
});

EmptyState.displayName = 'EmptyState';

/**
 * MultiModalContent Component - Main container
 * Fetches and displays images and tables from backend
 */
export default function MultiModalContent({ paperId }) {
  const store = useMultiModalStore();

  // Use React Query for data fetching with caching
  const { 
    data, 
    isLoading, 
    error, 
    refetch,
    isFetching 
  } = useQuery({
    queryKey: ['multimodal', paperId],
    queryFn: () => getMultiModalContent(paperId),
    enabled: !!paperId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
    retry: 2,
    refetchOnWindowFocus: false,
  });

  // Sync React Query data with Zustand store for global access
  useEffect(() => {
    if (data && paperId) {
      store.setContent(paperId, data);
      store.setError(paperId, null);
    }
  }, [data, paperId, store]);

  // Sync error state
  useEffect(() => {
    if (error && paperId) {
      store.setError(paperId, error.message);
    }
  }, [error, paperId, store]);

  // Memoize content arrays
  const images = useMemo(() => data?.images || [], [data?.images]);
  const tables = useMemo(() => data?.tables || [], [data?.tables]);
  
  const hasImages = images.length > 0;
  const hasTables = tables.length > 0;
  const hasContent = hasImages || hasTables;

  // Memoize refresh handler
  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // Loading state
  if (isLoading) {
    return (
      <Card className="p-8">
        <div className="flex flex-col items-center justify-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <div className="text-center space-y-1">
            <p className="font-medium">Loading Multi-Modal Content</p>
            <p className="text-sm text-muted-foreground">
              Extracting images and tables from paper...
            </p>
          </div>
        </div>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card className="p-8">
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center">
            <AlertCircle className="h-8 w-8 text-destructive" />
          </div>
          <div className="text-center space-y-2">
            <h3 className="font-medium">Failed to Load Content</h3>
            <p className="text-sm text-muted-foreground max-w-md">
              {error.message || 'An error occurred while loading images and tables.'}
            </p>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleRefresh}
              disabled={isFetching}
            >
              {isFetching ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Retrying...
                </>
              ) : (
                <>
                  <RefreshCcw className="h-4 w-4 mr-2" />
                  Retry
                </>
              )}
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  // Empty state
  if (!hasContent) {
    return <EmptyState type="empty" />;
  }

  // Success state - render content
  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <Badge variant="secondary" className="bg-blue-100 text-blue-800">
            <ImageIcon className="h-3 w-3 mr-1" />
            {data.total_images} {data.total_images === 1 ? 'Image' : 'Images'}
          </Badge>
          <Badge variant="secondary" className="bg-green-100 text-green-800">
            <TableIcon className="h-3 w-3 mr-1" />
            {data.total_tables} {data.total_tables === 1 ? 'Table' : 'Tables'}
          </Badge>
        </div>
        
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={handleRefresh}
          disabled={isFetching}
        >
          {isFetching ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCcw className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Content Tabs */}
      <Tabs defaultValue={hasImages ? 'images' : 'tables'} className="w-full">
        <TabsList className="w-full">
          {hasImages && (
            <TabsTrigger value="images" className="flex-1">
              <ImageIcon className="h-4 w-4 mr-2" />
              Images ({images.length})
            </TabsTrigger>
          )}
          {hasTables && (
            <TabsTrigger value="tables" className="flex-1">
              <TableIcon className="h-4 w-4 mr-2" />
              Tables ({tables.length})
            </TabsTrigger>
          )}
        </TabsList>

        {/* Images Tab */}
        {hasImages && (
          <TabsContent value="images" className="space-y-4 mt-4">
            {images.map((img, index) => (
              <ImageContent key={`${img.page}-${index}`} image={img} index={index} />
            ))}
          </TabsContent>
        )}

        {/* Tables Tab */}
        {hasTables && (
          <TabsContent value="tables" className="space-y-4 mt-4">
            {tables.map((tbl, index) => (
              <TableContent key={`${tbl.page}-${index}`} table={tbl} index={index} />
            ))}
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}