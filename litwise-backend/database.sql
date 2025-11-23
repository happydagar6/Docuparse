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