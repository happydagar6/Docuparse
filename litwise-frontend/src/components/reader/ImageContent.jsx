'use client';

import { memo, useState, useCallback, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Image as ImageIcon, ZoomIn, ZoomOut, Maximize2, X } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import Image from 'next/image';

/**
 * ImageContent Component - Displays a single image with caption
 * Memoized to prevent unnecessary re-renders
 */
export const ImageContent = memo(function ImageContent({ image, index }) {
  const [zoomed, setZoomed] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);

  // Memoize image src to prevent recalculation
  const imageSrc = useMemo(() => {
    if (!image?.image_base64) return null;
    return `data:image/${image.format || 'png'};base64,${image.image_base64}`;
  }, [image?.image_base64, image?.format]);

  // Callbacks memoized to prevent re-creation
  const toggleZoom = useCallback(() => {
    setZoomed(prev => !prev);
  }, []);

  const openFullscreen = useCallback(() => {
    setFullscreen(true);
  }, []);

  const closeFullscreen = useCallback(() => {
    setFullscreen(false);
    setZoomed(false);
  }, []);

  const handleImageLoad = useCallback(() => {
    setImageLoaded(true);
    setImageError(false);
  }, []);

  const handleImageError = useCallback(() => {
    setImageError(true);
    setImageLoaded(false);
  }, []);

  if (!image) return null;

  return (
    <>
      <Card className="overflow-hidden transition-all hover:shadow-md">
        <div className="p-4 space-y-3">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-linear-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-sm">
                <ImageIcon className="h-4 w-4 text-white" />
              </div>
              <div>
                <p className="text-sm font-medium">Figure {index + 1}</p>
                <p className="text-xs text-muted-foreground">
                  Page {image.page} • {image.width}×{image.height}px
                </p>
              </div>
            </div>
            
            {/* Action buttons */}
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleZoom}
                className="h-8 w-8 p-0"
                title={zoomed ? 'Zoom out' : 'Zoom in'}
              >
                {zoomed ? <ZoomOut className="h-4 w-4" /> : <ZoomIn className="h-4 w-4" />}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={openFullscreen}
                className="h-8 w-8 p-0"
                title="Fullscreen"
              >
                <Maximize2 className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Image */}
          {imageSrc && (
            <div 
              className={`
                relative overflow-hidden rounded-lg border bg-muted/30
                transition-all duration-300
                ${zoomed ? 'cursor-zoom-out' : 'cursor-zoom-in'}
              `}
              onClick={toggleZoom}
            >
              {!imageLoaded && !imageError && (
                <div className="absolute inset-0 flex items-center justify-center bg-muted">
                  <div className="text-sm text-muted-foreground">Loading...</div>
                </div>
              )}
              
              {imageError && (
                <div className="absolute inset-0 flex items-center justify-center bg-muted">
                  <div className="text-sm text-destructive">Failed to load image</div>
                </div>
              )}
              
              <Image
                src={imageSrc}
                alt={image.caption || `Figure ${index + 1}`}
                className={`
                  w-full h-auto transition-transform duration-300
                  ${zoomed ? 'scale-150' : 'scale-100'}
                  ${imageLoaded ? 'opacity-100' : 'opacity-0'}
                `}
                onLoad={handleImageLoad}
                onError={handleImageError}
                loading="lazy"
              />
            </div>
          )}

          {/* Caption */}
          {image.caption && (
            <div className="pt-2 border-t">
              <p className="text-sm text-muted-foreground leading-relaxed">
                <span className="font-medium">Caption:</span> {image.caption}
              </p>
            </div>
          )}

          {/* Format badge */}
          <div className="flex gap-2">
            <Badge variant="secondary" className="text-xs">
              {image.format?.toUpperCase() || 'IMAGE'}
            </Badge>
          </div>
        </div>
      </Card>

      {/* Fullscreen Dialog */}
      <Dialog open={fullscreen} onOpenChange={closeFullscreen}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>Figure {index + 1} - Page {image.page}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {imageSrc && (
              <div className="flex justify-center bg-muted/30 rounded-lg p-4">
                <Image
                  src={imageSrc}
                  alt={image.caption || `Figure ${index + 1}`}
                  className="max-w-full h-auto"
                />
              </div>
            )}
            {image.caption && (
              <div className="text-sm text-muted-foreground">
                <span className="font-medium">Caption:</span> {image.caption}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
});

ImageContent.displayName = 'ImageContent';