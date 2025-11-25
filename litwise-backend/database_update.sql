-- Database schema update to support separate AI processing
-- Run this SQL in your Supabase SQL editor

-- Add new columns to track processing status
ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'uploaded' CHECK (processing_status IN ('uploaded', 'processing', 'completed', 'failed')),
ADD COLUMN IF NOT EXISTS ai_generated_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS processing_error TEXT;

-- Update existing records to have default status
UPDATE papers 
SET processing_status = 'completed', ai_generated_at = updated_at 
WHERE summary IS NOT NULL AND processing_status = 'uploaded';

-- Add index for processing status queries
CREATE INDEX IF NOT EXISTS idx_papers_processing_status ON papers(processing_status);

-- Update the summary column to allow NULL (for uploaded but not processed papers)
ALTER TABLE papers ALTER COLUMN summary DROP NOT NULL;