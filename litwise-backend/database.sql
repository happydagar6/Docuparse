-- Enable UUID extension (for Supabase Auth integration)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table (for user-paper association; optional but scalable)
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create papers table
CREATE TABLE IF NOT EXISTS papers (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,  -- FK to users (nullable if no auth)
    title TEXT NOT NULL,
    summary JSONB NOT NULL,  -- Stores AI output: {"key_points": [...], "citations": [...], "related_works": [...]}
    content_text TEXT,  -- Optional: Raw extracted text (for quick search; index for large data)
    embedding_id TEXT,  -- Optional: Qdrant point ID (links to vector DB)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexes for scalability (fast queries on large datasets)
CREATE INDEX IF NOT EXISTS idx_papers_user_id ON papers(user_id);
CREATE INDEX IF NOT EXISTS idx_papers_title ON papers USING GIN (to_tsvector('english', title));  -- Full-text search
CREATE INDEX IF NOT EXISTS idx_papers_summary ON papers USING GIN(summary);  -- JSONB search

-- Enable RLS for security (users see only their papers)
ALTER TABLE papers ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can insert/read their own papers (adjust if using Supabase Auth)
CREATE POLICY "Users can insert own papers" ON papers
    FOR INSERT WITH CHECK (auth.uid()::uuid = user_id OR user_id IS NULL);  -- Allow anon inserts if no auth

CREATE POLICY "Users can view own papers" ON papers
    FOR SELECT USING (auth.uid()::uuid = user_id OR user_id IS NULL);

CREATE POLICY "Users can update own papers" ON papers
    FOR UPDATE USING (auth.uid()::uuid = user_id);

CREATE POLICY "Users can delete own papers" ON papers
    FOR DELETE USING (auth.uid()::uuid = user_id);

-- For users table (if using Auth)
CREATE POLICY "Public profiles are viewable by everyone" ON users
    FOR SELECT USING (true);

-- Trigger for auto-updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_papers_updated_at BEFORE UPDATE
    ON papers FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE
    ON users FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();


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



-- Add Paper Metadata Fields for Enhanced Search
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




-- Chat system database schema
-- Run this SQL in your Supabase SQL editor after the existing database_update.sql

-- Chat Sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id TEXT -- For future user system integration
);

-- Chat Messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat Memory table (for conversation summaries and memory management)
CREATE TABLE IF NOT EXISTS chat_memory (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    memory_type TEXT NOT NULL CHECK (memory_type IN ('summary', 'buffer')),
    content JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chat_sessions_paper_id ON chat_sessions(paper_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_memory_session_id ON chat_memory(session_id);

-- Update function for chat_sessions updated_at
CREATE OR REPLACE FUNCTION update_chat_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at for chat_sessions
DROP TRIGGER IF EXISTS trigger_update_chat_sessions_updated_at ON chat_sessions;
CREATE TRIGGER trigger_update_chat_sessions_updated_at
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_sessions_updated_at();

-- Update function for chat_memory updated_at
CREATE OR REPLACE FUNCTION update_chat_memory_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at for chat_memory
DROP TRIGGER IF EXISTS trigger_update_chat_memory_updated_at ON chat_memory;
CREATE TRIGGER trigger_update_chat_memory_updated_at
    BEFORE UPDATE ON chat_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_memory_updated_at();



-- ============================================
-- SYNTHESIS HISTORY DATABASE SCHEMA
-- ============================================
-- Purpose: Store AI-generated research syntheses for future reference
-- Date: 2025-11-30
-- Run this in Supabase SQL Editor

-- Create synthesis_history table
CREATE TABLE IF NOT EXISTS synthesis_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    
    -- Query information
    query TEXT NOT NULL,
    paper_count INTEGER NOT NULL DEFAULT 0,
    max_papers INTEGER NOT NULL DEFAULT 20,
    
    -- Synthesis results (stored as JSONB for flexibility)
    themes JSONB DEFAULT '[]'::jsonb,
    key_findings JSONB DEFAULT '[]'::jsonb,
    research_gaps JSONB DEFAULT '[]'::jsonb,
    trends JSONB DEFAULT '{}'::jsonb,
    top_papers JSONB DEFAULT '[]'::jsonb,
    
    -- Metadata
    paper_ids TEXT[] DEFAULT ARRAY[]::TEXT[],  -- Array of paper IDs used in synthesis
    search_results JSONB DEFAULT '[]'::jsonb,  -- Full search results for reproducibility
    
    -- User information (for future multi-user support)
    user_id TEXT,  -- Optional: link to auth.users if using Supabase Auth
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Optional: Add tags for organization
    tags TEXT[] DEFAULT ARRAY[]::TEXT[]
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_synthesis_history_query ON synthesis_history USING GIN(to_tsvector('english', query));
CREATE INDEX IF NOT EXISTS idx_synthesis_history_created_at ON synthesis_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_synthesis_history_user_id ON synthesis_history(user_id);
CREATE INDEX IF NOT EXISTS idx_synthesis_history_tags ON synthesis_history USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_synthesis_history_themes ON synthesis_history USING GIN(themes);
CREATE INDEX IF NOT EXISTS idx_synthesis_history_paper_ids ON synthesis_history USING GIN(paper_ids);

-- Comments for documentation
COMMENT ON TABLE synthesis_history IS 'Stores AI-generated research syntheses for historical reference and analysis';
COMMENT ON COLUMN synthesis_history.query IS 'Original search query used to generate synthesis';
COMMENT ON COLUMN synthesis_history.paper_count IS 'Number of papers analyzed in this synthesis';
COMMENT ON COLUMN synthesis_history.max_papers IS 'Maximum number of papers allowed by slider setting';
COMMENT ON COLUMN synthesis_history.themes IS 'Array of themes identified: [{"name": str, "description": str, "count": int, "papers": [...]}]';
COMMENT ON COLUMN synthesis_history.key_findings IS 'Array of key findings: ["finding 1", "finding 2", ...]';
COMMENT ON COLUMN synthesis_history.research_gaps IS 'Array of research gaps: ["gap 1", "gap 2", ...]';
COMMENT ON COLUMN synthesis_history.trends IS 'Temporal trends object: {"timeline": [...], "trend_description": str}';
COMMENT ON COLUMN synthesis_history.top_papers IS 'Top papers array: [{"id": str, "title": str, "relevance": float, "year": int}]';
COMMENT ON COLUMN synthesis_history.paper_ids IS 'Array of paper IDs used in this synthesis';
COMMENT ON COLUMN synthesis_history.search_results IS 'Full search results stored for reproducibility';
COMMENT ON COLUMN synthesis_history.tags IS 'Custom tags for organizing syntheses';

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_synthesis_history_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_synthesis_history_updated_at ON synthesis_history;
CREATE TRIGGER trigger_update_synthesis_history_updated_at
    BEFORE UPDATE ON synthesis_history
    FOR EACH ROW
    EXECUTE FUNCTION update_synthesis_history_updated_at();

-- Enable Row Level Security (optional, for multi-user support)
ALTER TABLE synthesis_history ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can view their own syntheses (adjust for your auth setup)
CREATE POLICY "Users can view own syntheses" ON synthesis_history
    FOR SELECT USING (
        user_id IS NULL OR  -- Allow viewing if no user_id (public)
        user_id = auth.uid()::text  -- Or if user_id matches authenticated user
    );

-- RLS Policy: Users can insert their own syntheses
CREATE POLICY "Users can insert own syntheses" ON synthesis_history
    FOR INSERT WITH CHECK (
        user_id IS NULL OR 
        user_id = auth.uid()::text
    );

-- RLS Policy: Users can update their own syntheses (e.g., add tags)
CREATE POLICY "Users can update own syntheses" ON synthesis_history
    FOR UPDATE USING (
        user_id IS NULL OR 
        user_id = auth.uid()::text
    );

-- RLS Policy: Users can delete their own syntheses
CREATE POLICY "Users can delete own syntheses" ON synthesis_history
    FOR DELETE USING (
        user_id IS NULL OR 
        user_id = auth.uid()::text
    );

-- Create view for summary statistics (optional but useful)
CREATE OR REPLACE VIEW synthesis_stats AS
SELECT 
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as total_syntheses,
    AVG(paper_count) as avg_papers_per_synthesis,
    COUNT(DISTINCT query) as unique_queries
FROM synthesis_history
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;

COMMENT ON VIEW synthesis_stats IS 'Daily statistics for synthesis generation';




CREATE TABLE IF NOT EXISTS literature_reviews (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    topic TEXT NOT NULL,
    review_style TEXT NOT NULL CHECK (review_style IN ('narrative', 'systematic', 'critical')),
    paper_ids TEXT[] NOT NULL,
    paper_count INTEGER NOT NULL DEFAULT 0,
    content JSONB NOT NULL,
    word_count INTEGER DEFAULT 0,
    user_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_literature_reviews_topic ON literature_reviews USING GIN(to_tsvector('english', topic));
CREATE INDEX IF NOT EXISTS idx_literature_reviews_created_at ON literature_reviews(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_literature_reviews_paper_ids ON literature_reviews USING GIN(paper_ids);

-- Auto-update timestamp
CREATE OR REPLACE FUNCTION update_literature_reviews_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_literature_reviews_updated_at ON literature_reviews;
CREATE TRIGGER trigger_update_literature_reviews_updated_at
    BEFORE UPDATE ON literature_reviews
    FOR EACH ROW
    EXECUTE FUNCTION update_literature_reviews_updated_at();



-- -- ============================================
-- -- ZOTERO INTEGRATION SCHEMA
-- -- Date: 2025-12-07
-- -- Purpose: Support Zotero import/export functionality
-- -- ============================================

-- -- Add zotero_id column to papers table for linking
-- ALTER TABLE papers 
-- ADD COLUMN IF NOT EXISTS zotero_id TEXT UNIQUE;

-- -- Add zotero_metadata column for storing original Zotero data
-- ALTER TABLE papers 
-- ADD COLUMN IF NOT EXISTS zotero_metadata JSONB;

-- -- Add zotero_sync_status for tracking sync state
-- ALTER TABLE papers 
-- ADD COLUMN IF NOT EXISTS zotero_sync_status TEXT DEFAULT 'not_synced' 
-- CHECK (zotero_sync_status IN ('not_synced', 'synced', 'sync_failed', 'modified'));

-- -- Add zotero_last_sync timestamp
-- ALTER TABLE papers 
-- ADD COLUMN IF NOT EXISTS zotero_last_sync TIMESTAMP WITH TIME ZONE;

-- -- Create index for fast Zotero lookups
-- CREATE INDEX IF NOT EXISTS idx_papers_zotero_id ON papers(zotero_id);
-- CREATE INDEX IF NOT EXISTS idx_papers_zotero_sync_status ON papers(zotero_sync_status);

-- -- Create zotero_connections table for storing user credentials
-- CREATE TABLE IF NOT EXISTS zotero_connections (
--     id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
--     user_id UUID REFERENCES users(id) ON DELETE CASCADE,
--     library_id TEXT NOT NULL,
--     library_type TEXT NOT NULL CHECK (library_type IN ('user', 'group')),
--     api_key_encrypted TEXT NOT NULL,  -- Store encrypted
--     connection_name TEXT DEFAULT 'My Zotero Library',
--     is_active BOOLEAN DEFAULT true,
--     last_sync TIMESTAMP WITH TIME ZONE,
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
--     updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
--     UNIQUE(user_id, library_id)
-- );

-- -- Enable RLS for zotero_connections
-- ALTER TABLE zotero_connections ENABLE ROW LEVEL SECURITY;

-- CREATE POLICY "Users can manage own Zotero connections" ON zotero_connections
--     FOR ALL USING (auth.uid()::uuid = user_id OR user_id IS NULL);

-- -- Create zotero_sync_log table for debugging
-- CREATE TABLE IF NOT EXISTS zotero_sync_log (
--     id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
--     connection_id UUID REFERENCES zotero_connections(id) ON DELETE CASCADE,
--     operation TEXT NOT NULL,  -- 'import', 'export', 'sync'
--     status TEXT NOT NULL,  -- 'success', 'failed', 'partial'
--     items_processed INTEGER DEFAULT 0,
--     items_failed INTEGER DEFAULT 0,
--     error_message TEXT,
--     details JSONB,
--     created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
-- );

-- -- Add trigger for zotero_connections updated_at
-- CREATE TRIGGER update_zotero_connections_updated_at BEFORE UPDATE
--     ON zotero_connections FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- -- Comments for documentation
-- COMMENT ON COLUMN papers.zotero_id IS 'Zotero item key for bidirectional sync';
-- COMMENT ON COLUMN papers.zotero_metadata IS 'Original Zotero item data (creators, dateAdded, tags, collections, etc.)';
-- COMMENT ON COLUMN papers.zotero_sync_status IS 'Sync state: not_synced, synced, sync_failed, modified';
-- COMMENT ON TABLE zotero_connections IS 'Stores user Zotero library connections (credentials)';
-- COMMENT ON TABLE zotero_sync_log IS 'Audit log for Zotero sync operations';







-- Enhanced Citation Management Tables
-- Purpose: Store extracted citations from papers with AI context

-- Table to store citations extracted from papers
CREATE TABLE IF NOT EXISTS paper_citations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    
    -- Citation identification
    citation_text TEXT NOT NULL,  -- Raw citation text from bibliography
    in_text_refs TEXT[],  -- In-text references like ["[15]", "Smith et al. (2020)"]
    
    -- Extracted metadata
    title TEXT,
    authors JSONB DEFAULT '[]'::jsonb,
    year INTEGER,
    doi TEXT,
    venue TEXT,  -- Journal/Conference
    
    -- AI-generated context
    relevance_summary TEXT,  -- AI summary of why this citation is relevant
    citation_context TEXT[],  -- Surrounding text where citation appears
    
    -- Citation counts and importance
    mention_count INTEGER DEFAULT 1,  -- How many times cited in the paper
    importance_score FLOAT DEFAULT 0.0,  -- AI-calculated importance (0-1)
    
    -- Metadata
    extraction_method TEXT DEFAULT 'auto',  -- 'auto', 'manual', 'ai-enhanced'
    citation_type TEXT,  -- 'background', 'method', 'comparison', 'data'
    verified BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    
    UNIQUE(paper_id, citation_text)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_paper_citations_paper_id ON paper_citations(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_citations_doi ON paper_citations(doi) WHERE doi IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_paper_citations_title ON paper_citations USING GIN (to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_paper_citations_authors ON paper_citations USING GIN(authors);
CREATE INDEX IF NOT EXISTS idx_paper_citations_importance ON paper_citations(importance_score DESC);

-- Table for citation network analysis
CREATE TABLE IF NOT EXISTS citation_relationships (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    citing_paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    cited_paper_id UUID REFERENCES papers(id) ON DELETE SET NULL,  -- Nullable if cited paper not in library
    citation_id UUID NOT NULL REFERENCES paper_citations(id) ON DELETE CASCADE,
    
    relationship_type TEXT DEFAULT 'cites',  -- 'cites', 'extends', 'contradicts', 'supports'
    confidence_score FLOAT DEFAULT 1.0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    
    UNIQUE(citing_paper_id, citation_id)
);

CREATE INDEX IF NOT EXISTS idx_citation_relationships_citing ON citation_relationships(citing_paper_id);
CREATE INDEX IF NOT EXISTS idx_citation_relationships_cited ON citation_relationships(cited_paper_id);

-- Enable RLS
ALTER TABLE paper_citations ENABLE ROW LEVEL SECURITY;
ALTER TABLE citation_relationships ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own paper citations" ON paper_citations
    FOR SELECT USING (
        paper_id IN (SELECT id FROM papers WHERE auth.uid()::uuid = user_id OR user_id IS NULL)
    );

CREATE POLICY "Users can manage own paper citations" ON paper_citations
    FOR ALL USING (
        paper_id IN (SELECT id FROM papers WHERE auth.uid()::uuid = user_id OR user_id IS NULL)
    );

-- Trigger for updated_at
CREATE TRIGGER update_paper_citations_updated_at BEFORE UPDATE
    ON paper_citations FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- Comments
COMMENT ON TABLE paper_citations IS 'Stores citations extracted from papers with AI-generated context';
COMMENT ON COLUMN paper_citations.relevance_summary IS 'AI-generated summary explaining why this citation is relevant';
COMMENT ON COLUMN paper_citations.importance_score IS 'AI-calculated importance score (0-1) based on mention frequency and context';
COMMENT ON TABLE citation_relationships IS 'Tracks citation relationships between papers in the library';





-- Migration: Add content type filters (has_images, has_tables, has_equations)
-- Purpose: Enable Phase 1.1 filters for searching papers by content type

-- Add boolean columns for content type filtering
ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS has_images BOOLEAN DEFAULT FALSE;

ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS has_tables BOOLEAN DEFAULT FALSE;

ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS has_equations BOOLEAN DEFAULT FALSE;

-- Create indexes for efficient filtering
CREATE INDEX IF NOT EXISTS idx_papers_has_images ON papers(has_images) WHERE has_images = TRUE;
CREATE INDEX IF NOT EXISTS idx_papers_has_tables ON papers(has_tables) WHERE has_tables = TRUE;
CREATE INDEX IF NOT EXISTS idx_papers_has_equations ON papers(has_equations) WHERE has_equations = TRUE;

-- Add comments for documentation
COMMENT ON COLUMN papers.has_images IS 'Paper contains extracted images';
COMMENT ON COLUMN papers.has_tables IS 'Paper contains extracted tables';
COMMENT ON COLUMN papers.has_equations IS 'Paper contains mathematical equations/formulas';
