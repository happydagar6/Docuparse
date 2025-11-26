-- Add page_info column to papers table to store page mapping information
-- This supports accurate page references in search results

ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS page_info JSONB;

-- Add index for page_info searches if needed
CREATE INDEX IF NOT EXISTS idx_papers_page_info ON papers USING GIN(page_info);

-- Add processing_status column for tracking paper processing state
ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'uploaded' 
CHECK (processing_status IN ('uploaded', 'processing', 'completed', 'failed'));

-- Add processing_error column for error tracking
ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS processing_error TEXT;

-- Add file metadata columns for better file tracking
ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS file_size INTEGER DEFAULT 0;

ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS filename TEXT;

-- Update existing papers to have default processing status
UPDATE papers 
SET processing_status = 'completed' 
WHERE processing_status IS NULL;