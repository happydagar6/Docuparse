-- Migration: Add file_type column to papers table
-- Date: 2026-01-07
-- Purpose: Support multi-format document uploads (PDF, TXT, MD, CSV)

-- Add file_type column
ALTER TABLE papers
ADD COLUMN IF NOT EXISTS file_type VARCHAR(10) DEFAULT 'pdf';

-- Add comment for documentation
COMMENT ON COLUMN papers.file_type IS 'File extension without dot (pdf, txt, csv, md, docx)';

-- Create index for file type queries
CREATE INDEX IF NOT EXISTS idx_papers_file_type ON papers(file_type);

-- Update existing records to have 'pdf' as file_type
UPDATE papers
SET file_type = 'pdf'
WHERE file_type IS NULL;
