-- =====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES FOR LITWISE
-- =====================================================
-- This file enables RLS and creates policies for all tables
-- to ensure users can only access their own data
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.papers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.paper_citations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.synthesis_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.study_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.literature_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.citation_relationships ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- USERS TABLE POLICIES
-- =====================================================

-- Users can view their own profile
CREATE POLICY "Users can view their own profile"
  ON public.users
  FOR SELECT
  USING (auth.uid() = id);

-- Users can update their own profile
CREATE POLICY "Users can update their own profile"
  ON public.users
  FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- =====================================================
-- PAPERS TABLE POLICIES
-- =====================================================

-- Users can view their own papers
CREATE POLICY "Users can view their own papers"
  ON public.papers
  FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own papers
CREATE POLICY "Users can insert their own papers"
  ON public.papers
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own papers
CREATE POLICY "Users can update their own papers"
  ON public.papers
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own papers
CREATE POLICY "Users can delete their own papers"
  ON public.papers
  FOR DELETE
  USING (auth.uid() = user_id);

-- =====================================================
-- PAPER CITATIONS TABLE POLICIES
-- =====================================================

-- Users can view citations for their own papers
CREATE POLICY "Users can view citations for their own papers"
  ON public.paper_citations
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = paper_citations.paper_id
      AND papers.user_id = auth.uid()
    )
  );

-- Users can insert citations for their own papers
CREATE POLICY "Users can insert citations for their own papers"
  ON public.paper_citations
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = paper_citations.paper_id
      AND papers.user_id = auth.uid()
    )
  );

-- Users can update citations for their own papers
CREATE POLICY "Users can update citations for their own papers"
  ON public.paper_citations
  FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = paper_citations.paper_id
      AND papers.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = paper_citations.paper_id
      AND papers.user_id = auth.uid()
    )
  );

-- Users can delete citations for their own papers
CREATE POLICY "Users can delete citations for their own papers"
  ON public.paper_citations
  FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = paper_citations.paper_id
      AND papers.user_id = auth.uid()
    )
  );

-- =====================================================
-- CHAT SESSIONS TABLE POLICIES
-- =====================================================

-- Users can view chat sessions for their own papers
CREATE POLICY "Users can view their chat sessions"
  ON public.chat_sessions
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = chat_sessions.paper_id
      AND papers.user_id = auth.uid()
    )
  );

-- Users can create chat sessions for their own papers
CREATE POLICY "Users can create chat sessions"
  ON public.chat_sessions
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = chat_sessions.paper_id
      AND papers.user_id = auth.uid()
    )
  );

-- Users can update their own chat sessions
CREATE POLICY "Users can update their chat sessions"
  ON public.chat_sessions
  FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = chat_sessions.paper_id
      AND papers.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = chat_sessions.paper_id
      AND papers.user_id = auth.uid()
    )
  );

-- Users can delete their own chat sessions
CREATE POLICY "Users can delete their chat sessions"
  ON public.chat_sessions
  FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = chat_sessions.paper_id
      AND papers.user_id = auth.uid()
    )
  );

-- =====================================================
-- CHAT MESSAGES TABLE POLICIES
-- =====================================================

-- Users can view messages in their chat sessions
CREATE POLICY "Users can view their chat messages"
  ON public.chat_messages
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.chat_sessions
      JOIN public.papers ON papers.id = chat_sessions.paper_id
      WHERE chat_sessions.id = chat_messages.session_id
      AND papers.user_id = auth.uid()
    )
  );

-- Users can create messages in their chat sessions
CREATE POLICY "Users can create chat messages"
  ON public.chat_messages
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.chat_sessions
      JOIN public.papers ON papers.id = chat_sessions.paper_id
      WHERE chat_sessions.id = chat_messages.session_id
      AND papers.user_id = auth.uid()
    )
  );

-- =====================================================
-- CHAT MEMORY TABLE POLICIES
-- =====================================================

-- Users can view memory for their chat sessions
CREATE POLICY "Users can view their chat memory"
  ON public.chat_memory
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.chat_sessions
      JOIN public.papers ON papers.id = chat_sessions.paper_id
      WHERE chat_sessions.id = chat_memory.session_id
      AND papers.user_id = auth.uid()
    )
  );

-- Users can insert/update memory for their chat sessions
CREATE POLICY "Users can manage their chat memory"
  ON public.chat_memory
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.chat_sessions
      JOIN public.papers ON papers.id = chat_sessions.paper_id
      WHERE chat_sessions.id = chat_memory.session_id
      AND papers.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.chat_sessions
      JOIN public.papers ON papers.id = chat_sessions.paper_id
      WHERE chat_sessions.id = chat_memory.session_id
      AND papers.user_id = auth.uid()
    )
  );

-- =====================================================
-- SYNTHESIS HISTORY TABLE POLICIES
-- =====================================================

-- Note: synthesis_history.user_id is TEXT, not UUID
-- We need to convert auth.uid() to text for comparison

-- Users can view their own synthesis history
CREATE POLICY "Users can view their synthesis history"
  ON public.synthesis_history
  FOR SELECT
  USING (auth.uid()::text = user_id);

-- Users can create their own synthesis history
CREATE POLICY "Users can create synthesis history"
  ON public.synthesis_history
  FOR INSERT
  WITH CHECK (auth.uid()::text = user_id);

-- Users can update their own synthesis history
CREATE POLICY "Users can update their synthesis history"
  ON public.synthesis_history
  FOR UPDATE
  USING (auth.uid()::text = user_id)
  WITH CHECK (auth.uid()::text = user_id);

-- Users can delete their own synthesis history
CREATE POLICY "Users can delete their synthesis history"
  ON public.synthesis_history
  FOR DELETE
  USING (auth.uid()::text = user_id);

-- =====================================================
-- STUDY PLANS TABLE POLICIES
-- =====================================================

-- Users can view study plans for their own papers
CREATE POLICY "Users can view their study plans"
  ON public.study_plans
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = study_plans.paper_id
      AND papers.user_id = auth.uid()
    )
  );

-- Users can create study plans for their own papers
CREATE POLICY "Users can create study plans"
  ON public.study_plans
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = study_plans.paper_id
      AND papers.user_id = auth.uid()
    )
  );

-- Users can delete their own study plans
CREATE POLICY "Users can delete study plans"
  ON public.study_plans
  FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = study_plans.paper_id
      AND papers.user_id = auth.uid()
    )
  );

-- =====================================================
-- LITERATURE REVIEWS TABLE POLICIES
-- =====================================================

-- Note: literature_reviews.user_id is TEXT, not UUID

-- Users can view their own literature reviews
CREATE POLICY "Users can view their literature reviews"
  ON public.literature_reviews
  FOR SELECT
  USING (auth.uid()::text = user_id);

-- Users can create their own literature reviews
CREATE POLICY "Users can create literature reviews"
  ON public.literature_reviews
  FOR INSERT
  WITH CHECK (auth.uid()::text = user_id);

-- Users can update their own literature reviews
CREATE POLICY "Users can update their literature reviews"
  ON public.literature_reviews
  FOR UPDATE
  USING (auth.uid()::text = user_id)
  WITH CHECK (auth.uid()::text = user_id);

-- Users can delete their own literature reviews
CREATE POLICY "Users can delete their literature reviews"
  ON public.literature_reviews
  FOR DELETE
  USING (auth.uid()::text = user_id);

-- =====================================================
-- CITATION RELATIONSHIPS TABLE POLICIES
-- =====================================================

-- Users can view citation relationships for their own papers
CREATE POLICY "Users can view their citation relationships"
  ON public.citation_relationships
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE (papers.id = citation_relationships.citing_paper_id
         OR papers.id = citation_relationships.cited_paper_id)
      AND papers.user_id = auth.uid()
    )
  );

-- Users can create citation relationships for their own papers
CREATE POLICY "Users can create citation relationships"
  ON public.citation_relationships
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = citation_relationships.citing_paper_id
      AND papers.user_id = auth.uid()
    )
  );

-- Users can delete their own citation relationships
CREATE POLICY "Users can delete citation relationships"
  ON public.citation_relationships
  FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM public.papers
      WHERE papers.id = citation_relationships.citing_paper_id
      AND papers.user_id = auth.uid()
    )
  );

-- =====================================================
-- TRIGGER TO AUTO-CREATE USER RECORDS
-- =====================================================
-- This trigger automatically creates a user record when
-- someone signs up via Supabase Auth

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.users (id, email, created_at, updated_at)
  VALUES (
    NEW.id,
    NEW.email,
    NOW(),
    NOW()
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop trigger if exists (for idempotency)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Create trigger on auth.users table
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- =====================================================
-- GRANT SERVICE ROLE BYPASS (for backend API)
-- =====================================================
-- Service role can bypass RLS for admin operations
-- This is already enabled by default in Supabase

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================
-- Run these to verify RLS is properly configured:

-- Check if RLS is enabled on all tables:
-- SELECT tablename, rowsecurity 
-- FROM pg_tables 
-- WHERE schemaname = 'public' 
-- AND tablename IN ('users', 'papers', 'paper_citations', 'chat_sessions', 'chat_messages', 'chat_memory', 'synthesis_history', 'study_plans', 'literature_reviews', 'citation_relationships');

-- View all policies:
-- SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
-- FROM pg_policies
-- WHERE schemaname = 'public'
-- ORDER BY tablename, policyname;
