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
