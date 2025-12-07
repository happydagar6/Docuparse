"""
Vision Service for Image Captioning
Uses GPT-4 Vision to generate detailed descriptions of figures, charts, diagrams
"""

from openai import OpenAI
import os
from typing import List, Dict, Optional
import base64
import asyncio
import time


class VisionService:
    """Generate captions and descriptions for images using GPT-5-mini Vision."""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
        self.max_completion_tokens = 500  # Max tokens for caption generation
        
        
    def caption_image(self, image_base64: str, context: Optional[str] = None) -> str:
        """
        Generate detailed caption for a single image
        
        Args:
            image_base64: Base64 encoded image
            context: Optional context (e.g., surrounding text, page number)
        
        Returns:
            Detailed image description
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert at analyzing scientific figures, charts, and diagrams from research papers.

Your task:
1. Identify the type of visual (graph, chart, diagram, architecture, equation, screenshot, etc.)
2. Describe what the visual shows in detail
3. Extract key data points, trends, or insights
4. Note any labels, axes, legends, or annotations
5. Be concise but comprehensive (3-5 sentences)

Format: "This [type] shows [description]. [Key insights]. [Notable details]."
"""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Analyze this scientific figure/diagram. {f'Context: {context}' if context else ''}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=self.max_completion_tokens,
                temperature=0.3
            )
            
            caption = response.choices[0].message.content.strip()
            return caption
        
        except Exception as e:
            print(f"❌ Failed to generate caption: {e}")
            return f"[Image from page - caption generation failed]"
        
        
    def caption_batch(self, images: List[Dict], batch_size: int = 5, max_images: int = 50) -> List[Dict]:
        """
        Generate captions for multiple images in batches (limited to 50 images)
        
        Args:
            images: List of image dicts (must have 'image_base64' and 'page' keys)
            batch_size: Process N images at a time (to avoid rate limits)
            max_images: Maximum number of images to caption (default 50 to prevent rate limits)
        
        Returns:
            List of image dicts with added 'caption' key
        """
        total_images = len(images)
        
        # Limit captioning to first max_images to prevent rate limits and excessive costs
        if total_images > max_images:
            print(f"🎨 Generating captions for first {max_images}/{total_images} images (rate limit protection)...")
            images_to_caption = images[:max_images]
            remaining_images = images[max_images:]
        else:
            print(f"🎨 Generating captions for {total_images} images...")
            images_to_caption = images
            remaining_images = []
        
        # Use async batch processing for speed
        captioned_images = self._caption_batch_parallel(images_to_caption, max_concurrent=10)
        
        # Add placeholder captions for images beyond the limit
        if remaining_images:
            print(f"⚠️  Skipping {len(remaining_images)} images (beyond 50-image limit to prevent rate limits)")
            for img in remaining_images:
                img_with_caption = img.copy()
                img_with_caption['caption'] = f"Image on page {img['page']} (not captioned - exceeds 50-image limit)"
                img_with_caption['caption_length'] = len(img_with_caption['caption'])
                captioned_images.append(img_with_caption)
        
        print(f"✅ Caption generation complete: {min(total_images, max_images)} captioned, {max(0, total_images - max_images)} skipped")
        return captioned_images
    
    def _caption_batch_parallel(self, images: List[Dict], max_concurrent: int = 10) -> List[Dict]:
        """
        Process images in parallel with rate limit handling
        
        Args:
            images: List of image dicts
            max_concurrent: Maximum concurrent API calls (to avoid rate limits)
        
        Returns:
            List of captioned images
        """
        captioned_images = []
        total = len(images)
        
        # Process in chunks to respect rate limits
        chunk_size = max_concurrent
        
        for chunk_start in range(0, total, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total)
            chunk = images[chunk_start:chunk_end]
            
            print(f"   📦 Processing batch {chunk_start//chunk_size + 1} ({chunk_start+1}-{chunk_end}/{total})...")
            
            # Process chunk with delays between requests
            for i, img in enumerate(chunk):
                try:
                    global_idx = chunk_start + i + 1
                    
                    # Create context
                    context = f"This image appears on page {img['page']} of a research paper"
                    
                    # Generate caption with retry logic
                    caption = self._caption_with_retry(img['image_base64'], context, max_retries=2)
                    
                    # Add caption to image
                    img_with_caption = img.copy()
                    img_with_caption['caption'] = caption
                    img_with_caption['caption_length'] = len(caption)
                    
                    captioned_images.append(img_with_caption)
                    
                    if global_idx % 10 == 0 or global_idx == total:
                        print(f"   ✅ Processed {global_idx}/{total} images")
                    
                    # Small delay to avoid rate limits (0.3s = ~3 requests/sec)
                    if i < len(chunk) - 1:  # Don't delay after last image in chunk
                        time.sleep(0.3)
                    
                except Exception as e:
                    print(f"   ⚠️  Failed image {chunk_start + i + 1}: {str(e)[:100]}")
                    # Add fallback caption
                    img_with_caption = img.copy()
                    img_with_caption['caption'] = f"[Image on page {img['page']} - caption failed]"
                    captioned_images.append(img_with_caption)
            
            # Longer pause between chunks
            if chunk_end < total:
                print(f"   ⏸️  Pausing 2s before next batch...")
                time.sleep(2)
        
        return captioned_images
    
    def _caption_with_retry(self, image_base64: str, context: str, max_retries: int = 2) -> str:
        """Generate caption with exponential backoff retry"""
        for attempt in range(max_retries + 1):
            try:
                return self.caption_image(image_base64, context)
            except Exception as e:
                if attempt < max_retries and "rate_limit" in str(e).lower():
                    wait_time = (2 ** attempt) * 0.5  # 0.5s, 1s, 2s
                    print(f"   ⏳ Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                elif attempt == max_retries:
                    return f"[Image - caption generation failed]"
        
        return f"[Image - caption generation failed]"


# Singleton instance
vision_service = VisionService()