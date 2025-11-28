-- Migration: Add Paper Metadata Fields for Enhanced Search
-- Date: 2025-11-28
-- Purpose: Enable advanced filtering by author, year, DOI, and keywords

-- Add metadata columns to papers table
ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS authors JSONB DEFAULT '[]'::jsonb;

ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS publication_year INTEGER;

ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS doi TEXT;

ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS keywords TEXT[] DEFAULT ARRAY[]::TEXT[];

ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS journal_or_conference TEXT;

ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS abstract TEXT;

-- Create indexes for efficient filtering and searching
CREATE INDEX IF NOT EXISTS idx_papers_authors ON papers USING GIN(authors);
CREATE INDEX IF NOT EXISTS idx_papers_publication_year ON papers(publication_year);
CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_papers_keywords ON papers USING GIN(keywords);
CREATE INDEX IF NOT EXISTS idx_papers_abstract ON papers USING GIN(to_tsvector('english', abstract));

-- Add comments for documentation
COMMENT ON COLUMN papers.authors IS 'Array of author objects with name, affiliation, email';
COMMENT ON COLUMN papers.publication_year IS 'Year of publication (extracted from PDF or metadata)';
COMMENT ON COLUMN papers.doi IS 'Digital Object Identifier for the paper';
COMMENT ON COLUMN papers.keywords IS 'Array of keywords/tags for the paper';
COMMENT ON COLUMN papers.journal_or_conference IS 'Publication venue (journal or conference name)';
COMMENT ON COLUMN papers.abstract IS 'Paper abstract text for enhanced search';

-- Update existing papers to have default empty arrays/null values if needed
UPDATE papers 
SET 
    authors = COALESCE(authors, '[]'::jsonb),
    keywords = COALESCE(keywords, ARRAY[]::TEXT[])
WHERE 
    authors IS NULL OR keywords IS NULL;
